import os
import sys
import json
import time
import traceback
from datetime import datetime
import streamlit as st
from google import genai
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
        if key in st.secrets:
            return st.secrets[key]
    except Exception as e:
        st.warning(f"Secrets 파싱 경고 ({key}): {e}")
    return os.environ.get(key, "")

BLOG_ID = get_config_val("BLOG_ID") or "5571572496232571585"
CLIENT_SECRET_JSON_STR = get_config_val("BLOGGER_CLIENT_SECRET_JSON")
TOKEN_JSON_STR = get_config_val("BLOGGER_TOKEN_JSON")
GEMINI_API_KEY = get_config_val("GEMINI_API_KEY")

# 설정값 사전 디버그 점검 (화면 상단)
with st.expander("🔍 설정값 보관함 점검 상태 (클릭하여 확인)"):
    st.write(f"- **BLOG_ID**: {'✅ 설정됨' if BLOG_ID else '❌ 미설정'}")
    st.write(f"- **BLOGGER_CLIENT_SECRET_JSON**: {'✅ 설정됨' if CLIENT_SECRET_JSON_STR else '❌ 미설정'}")
    st.write(f"- **BLOGGER_TOKEN_JSON**: {'✅ 설정됨' if TOKEN_JSON_STR else '❌ 미설정'}")
    st.write(f"- **GEMINI_API_KEY**: {'✅ 설정됨' if GEMINI_API_KEY else '❌ 미설정'}")

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
        st.code(traceback.format_exc())
        return None

def generate_blog_post(topic, keywords, tone, structure):
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY 설정값이 누락되었습니다. Streamlit Secrets을 확인해 주세요."

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        return None, f"Gemini Client 초기화 실패: {e}\n{traceback.format_exc()}"

    prompt = f"""
너는 전문 블로그 콘텐츠 에디터야. 구글 블로그스팟에 포스팅할 높은 품질의 SEO 최적화 글을 작성해줘.

[포스팅 가이드라인]
1. 주제: {topic}
2. 필수 포함 키워드: {keywords} (글 작성 시 자연스럽게 녹여서 작성해줘)
3. 말투 / 어조: {tone}
4. 원하는 글 구조:
{structure}

[작성 규칙]
- 검색 엔진(SEO)에 최적화된 매력적인 제목을 지어줘.
- HTML 태그(<h2>, <h3>, <p>, <ul>, <li>, <b>)를 적극 사용하여 가독성이 뛰어난 웹 서식으로 작성해줘.
- 반드시 다른 설명 없이 오직 순수한 JSON 형식으로만 응답해야 해.

[JSON 응답 스키마]
{{
  "title": "블로그 글 제목",
  "content": "<p>HTML 형식의 블로그 본문 내용...</p>",
  "labels": ["태그1", "태그2", "태그3"]
}}
"""

    models_to_try = ['gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-1.5-pro', 'gemini-2.0-flash']
    response_text = None
    errors_log = []

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            if response and response.text:
                response_text = response.text.strip()
                break
        except Exception as e:
            errors_log.append(f"[{model_name}] {e}")
            time.sleep(1)

    if not response_text:
        error_detail = "\n".join(errors_log)
        return None, f"모든 Gemini 모델 호출 실패.\n상세 오류 로그:\n{error_detail}"

    try:
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()

        return json.loads(response_text), None
    except Exception as e:
        today_str = datetime.now().strftime('%Y년 %m월 %d일')
        return {
            "title": f"[{today_str}] {topic}",
            "content": f"<div>{response_text}</div>",
            "labels": ["AI포스팅", "Gemini"]
        }, None

# UI 세팅
st.subheader("⚙️ 포스팅 설정")

input_topic = st.text_input("1. 블로그 주제", value="스마트폰 배터리 절약 및 수명 관리 팁")
input_keywords = st.text_input("2. 필수 키워드 (쉼표 구분)", value="스마트폰 배터리, 배터리 절약, 아이폰 배터리")
input_tone = st.selectbox("3. 말투 / 어조", [
    "친절하고 친근한 블로거 말투 (~해요, ~입니다)",
    "전문적이고 신뢰감 있는 서식 (~입니다, ~함)",
    "쉽고 위트 있는 일상 대화체"
])
input_structure = st.text_area("4. 글 구조 가이드라인", value="""1. 서론: 도입부
2. 본론 1: 주요 원인 (소제목 <h2>)
3. 본론 2: 효과적인 해결 팁 3가지 (소제목 <h2> 및 <ul>, <li>)
4. 본론 3: 주의사항 (소제목 <h2>)
5. 결론: 요약 및 마무리""", height=150)

st.divider()

if st.button("🚀 AI 글 작성 & 즉시 발행하기", type="primary", use_container_width=True):
    if not input_topic or not input_keywords:
        st.warning("주제와 키워드를 모두 입력해 주세요.")
    else:
        with st.status("글 발행 작업 진행 중...", expanded=True) as status:
            st.write("1️⃣ Gemini AI가 SEO 글을 생성하고 있습니다...")
            post_data, err_msg = generate_blog_post(input_topic, input_keywords, input_tone, input_structure)
            
            if not post_data:
                status.update(label="❌ AI 글 생성 실패", state="error")
                st.error("오류 발생 상세원인:")
                st.code(err_msg)
            else:
                st.write(f"✓ AI 글 생성 완료! 제목: **{post_data.get('title')}**")
                st.write("2️⃣ 구글 Blogger API로 포스팅 전송 중...")
                
                service = get_blogger_service()
                if service:
                    body = {
                        'kind': 'blogger#post',
                        'title': post_data.get('title'),
                        'content': post_data.get('content'),
                        'labels': post_data.get('labels', [])
                    }
                    try:
                        req = service.posts().insert(blogId=BLOG_ID, body=body)
                        res = req.execute()
                        status.update(label="🎉 발행 성공!", state="complete")
                        
                        st.balloons()
                        st.success(f"블로그 포스팅이 정상적으로 발행되었습니다!")
                        st.markdown(f"👉 **[발행된 글 보러가기]({res.get('url')})**")
                        st.info(f"글 제목: {res.get('title')}")
                    except Exception as err:
                        status.update(label="❌ Blogger 발행 실패", state="error")
                        st.error(f"Blogger 포스팅 중 오류 발생: {err}")
                        st.code(traceback.format_exc())
                else:
                    status.update(label="❌ 인증 오류", state="error")

st.divider()
st.caption("💡 스마트폰 브라우저에 이 페이지 주소를 즐겨찾기 해두시면 언제 어디서나 포스팅이 가능합니다.")
