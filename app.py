import os
import sys
import json
import time
import requests
import traceback
from datetime import datetime
import streamlit as st
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/blogger']

st.set_page_config(
    page_title="Blogger AI 자동 발행 대시보드",
    page_icon="📝",
    layout="centered"
)

st.title("📝 Blogger AI 포스팅 대시보드")
st.caption("주제와 키워드를 입력하고 버튼을 누르면 Gemini AI가 글을 작성하고 자동 발행합니다.")

def get_config_val(key):
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, "")

BLOG_ID = get_config_val("BLOG_ID") or "5571572496232571585"
CLIENT_SECRET_JSON_STR = get_config_val("BLOGGER_CLIENT_SECRET_JSON")
TOKEN_JSON_STR = get_config_val("BLOGGER_TOKEN_JSON")
GEMINI_API_KEY = get_config_val("GEMINI_API_KEY")

# 설정 상태
with st.expander("🔍 설정 상태 점검"):
    st.write(f"- BLOG_ID: {'✅ 설정됨' if BLOG_ID else '❌ 미설정'}")
    st.write(f"- CLIENT_SECRET: {'✅ 설정됨' if CLIENT_SECRET_JSON_STR else '❌ 미설정'}")
    st.write(f"- TOKEN: {'✅ 설정됨' if TOKEN_JSON_STR else '❌ 미설정'}")
    st.write(f"- GEMINI_API_KEY: {'✅ 설정됨' if GEMINI_API_KEY else '❌ 미설정'}")

def get_blogger_service():
    if not TOKEN_JSON_STR:
        st.error("BLOGGER_TOKEN_JSON 설정이 누락되었습니다.")
        return None

    try:
        token_info = json.loads(TOKEN_JSON_STR)
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)

        if creds and creds.expired and creds.refresh_token:
            if CLIENT_SECRET_JSON_STR:
                client_info = json.loads(CLIENT_SECRET_JSON_STR)
                installed_or_web = client_info.get('installed') or client_info.get('web')
                if installed_or_web:
                    creds.client_id = installed_or_web.get('client_id')
                    creds.client_secret = installed_or_web.get('client_secret')
                    creds.token_uri = installed_or_web.get('token_uri', 'https://oauth2.googleapis.com/token')

        creds.refresh(Request())
        return build('blogger', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Blogger 인증 오류: {e}")
        return None

def generate_blog_post(topic, keywords, tone, structure):
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY가 설정되지 않았습니다."

    clean_key = GEMINI_API_KEY.strip().strip("'").strip('"')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={clean_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""
너는 전문 블로그 콘텐츠 에디터야. 구글 블로그스팟에 포스팅할 높은 품질의 SEO 최적화 글을 작성해줘.

1. 주제: {topic}
2. 필수 포함 키워드: {keywords}
3. 말투: {tone}
4. 구조:
{structure}

반드시 순수한 JSON 형식으로만 응답해줘.
{{
  "title": "글 제목",
  "content": "<p>HTML 본문 내용...</p>",
  "labels": ["태그1", "태그2"]
}}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }

    last_err = ""
    for attempt in range(3):
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            res_json = res.json()

            if res.status_code == 200:
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "").strip()
                        if text.startswith("```"):
                            lines = text.splitlines()
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            if lines and lines[-1].startswith("```"):
                                lines = lines[:-1]
                            text = "\n".join(lines).strip()
                        return json.loads(text), None
            elif res.status_code == 429:
                last_err = f"429 요청 한도 대기 중 (7초 후 재시도... {attempt+1}/3)"
                time.sleep(7)
            else:
