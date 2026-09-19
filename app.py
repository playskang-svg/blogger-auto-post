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

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="Blogger AI 자동 발행 대시보드",
    page_icon="📝",
    layout="centered"
)

st.title("📝 Blogger AI 포스팅 대시보드")
st.caption("주제와 키워드를 입력하고 버튼을 누르면 Gemini AI가 글을 작성하고 자동 발행합니다.")

# --- 환경 변수 로드 ---
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

with st.expander("🔍 설정 상태 점검"):
    st.write(f"- BLOG_ID: {'✅ 설정됨' if BLOG_ID else '❌ 미설정'}")
    st.write(f"- CLIENT_SECRET: {'✅ 설정됨' if CLIENT_SECRET_JSON_STR else '❌ 미설정'}")
    st.write(f"- TOKEN: {'✅ 설정됨' if TOKEN_JSON_STR else '❌ 미설정'}")
    st.write(f"- GEMINI_API_KEY: {'✅ 설정됨' if GEMINI_API_KEY else '❌ 미설정'}")

# --- Blogger 서비스 인증 ---
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

# --- Gemini API 콘텐츠 생성 (429 에러 방어 로직 추가) ---
def generate_blog_post(topic, keywords, tone, structure, ad_code=""):
    if not GEMINI_API_KEY:
        return None, "GEMINI_API_KEY가 설정되지 않았습니다."

    clean_key = GEMINI_API_KEY.strip().strip("'").strip('"')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={clean_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""너는 전문 블로그 콘텐츠 에디터야. 구글 블로그스팟에 포스팅할 높은 품질의 SEO 최적화 글을 작성해줘.

[작성 조건]
- 주제: {topic}
- 키워드: {keywords}
- 어조: {tone}
- 구조: {structure}
- 출력 포맷: HTML 형식 (<h2>, <h3>, <p>, <ul>, <li>, <div> 등 적절히 활용)
- 문체: 상투적이고 장식적인 문구 대신 구체적인 수치·기준·조건 중심으로 간결하게 작성

[디자인 스타일 규칙 - 아래 인라인 style을 모든 해당 태그에 그대로 적용할 것]:
- 문단(p): <p style="font-family:'Noto Sans KR','Malgun Gothic','Apple SD Gothic Neo',sans-serif;font-size:18px;line-height:1.85;color:#3d3d42;margin:0 0 20px;">...</p>
- 큰 소제목(h2): <h2 style="font-family:'Noto Sans KR','Malgun Gothic','Apple SD Gothic Neo',sans-serif;font-size:24px;font-weight:700;color:#2b2d33;margin:36px 0 16px;">...</h2>
- 작은 소제목(h3): <h3 style="font-family:'Noto Sans KR','Malgun Gothic','Apple SD Gothic Neo',sans-serif;font-size:20px;font-weight:700;color:#2b2d33;margin:28px 0 12px;">...</h3>
- 목록(ul): <ul style="font-family:'Noto Sans KR','Malgun Gothic','Apple SD Gothic Neo',sans-serif;font-size:18px;line-height:1.85;color:#3d3d42;padding-left:20px;margin:0 0 20px;">...</ul>
- 강조(strong): <strong style="color:#16181d;">...</strong>
- 핵심 포인트/팁 박스: <div style="background:#f8f8f9;border-left:4px solid #0f9d7a;border-radius:8px;padding:16px 20px;margin:24px 0;font-family:'Noto Sans KR','Malgun Gothic',sans-serif;font-size:16px;line-height:1.7;color:#2b2d33;"><strong style="color:#0f9d7a;">💡 TIP</strong><br/>...</div>
- 요약/체크리스트 박스: <div style="background:#fefaf3;border:1px solid #f0e4d0;border-radius:8px;padding:20px 24px;margin:28px 0;font-family:'Noto Sans KR','Malgun Gothic',sans-serif;"><strong style="color:#2b2d33;font-size:17px;">✅ 핵심 체크리스트</strong><ul style="margin:12px 0 0;padding-left:20px;color:#3d3d42;line-height:1.8;">...</ul></div>
- 주의사항 1: 결과물에 '블로그제목:' 이라는 텍스트는 절대 포함하지 말 것. 오직 본문만 작성할 것.
- 주의사항 2: 전달하는 광고 코드가 있을 경우, 구조가 절대 흐트러지지 않게 원본 그대로 본문에 삽입할 것.

광고 코드:
{ad_code if ad_code else '없음'}
"""
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    # 429 에러 발생 시 최대 3번까지 대기 후 재시도
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            # 429 에러(Too Many Requests)인 경우 대기 후 재시도
            if response.status_code == 429:
                wait_time = 7 * (attempt + 1)  # 7초, 14초 대기
                if attempt < max_retries - 1:
                    st.warning(f"⚠️ API 요청 한도 초과(429). {wait_time}초 후 다시 시도합니다... ({attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    return None, "API 요청 한도 초과(429)로 재시도에 실패했습니다. 1~2분 후 다시 시도해 주세요."
                    
            response.raise_for_status()
            
            result = response.json()
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
            
            # 마크다운 코드블럭 제거
            if generated_text.startswith("```"):
                lines = generated_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                generated_text = "\n".join(lines).strip()
                
            return generated_text, None
                
        except requests.exceptions.RequestException as err:
            return None, f"API 호출 중 에러 발생: {err}"
        except Exception as e:
            return None, f"알 수 없는 오류 발생: {e}"
            
    return None, "알 수 없는 이유로 API 호출에 실패했습니다."

# --- UI 및 실행 로직 ---
st.subheader("📝 포스팅 작성 설정")
topic = st.text_input("포스팅 주제", placeholder="예: 2026년 최신 IT 트렌드")
keywords = st.text_input("핵심 키워드", placeholder="예: 인공지능, 챗봇, 자동화 (쉼표로 구분)")

col1, col2 = st.columns(2)
with col1:
    tone = st.selectbox("어조 (Tone)", ["전문적인", "친근한", "유머러스한", "설득력 있는"])
with col2:
    structure = st.selectbox("글 구조", ["서론-본론-결론", "리스트형 (Top 5 등)", "Q&A 형식"])

ad_code_input = st.text_area("삽입할 광고 코드 (선택 사항)", placeholder="<script>...</script> 형식의 애드센스 등 코드")

if st.button("🚀 포스팅 생성 및 자동 발행하기"):
    if not topic:
        st.warning("포스팅 주제를 입력해주세요.")
    else:
        with st.spinner("Gemini AI가 포스팅을 작성 중입니다... (약 10~20초 소요)"):
            content, error = generate_blog_post(topic, keywords, tone, structure, ad_code_input)
            
            if error:
                st.error(error)
            else:
                st.success("✅ 포스팅 내용 생성 완료!")
                
                with st.expander("미리보기 및 HTML 소스 확인"):
                    st.markdown(content, unsafe_allow_html=True)
                    st.code(content, language='html')
                
                st.info("Blogger에 포스팅을 발행합니다...")
                
                service = get_blogger_service()
                if service:
                    try:
                        post_body = {
                            "title": topic,
                            "content": content
                        }
                        
                        request = service.posts().insert(blogId=BLOG_ID, body=post_body)
                        response = request.execute()
                        
                        st.success(f"🎉 성공적으로 발행되었습니다! [포스트 보러가기]({response.get('url')})")
                    except Exception as e:
                        st.error(f"Blogger 발행 중 오류 발생: {e}")
                else:
                    st.error("Blogger 서비스 인증에 실패하여 발행하지 못했습니다. 설정 상태를 확인해 주세요.")
