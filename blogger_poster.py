import os
import sys
import json
import time
import requests
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/blogger']

# ============================================================
# [블로그 포스팅 맞춤 설정]
# ============================================================
BLOG_CONFIG = {
    "topic": "스마트폰 및 IT 실용 팁 / 정보",
    "keywords": ["아이폰 꿀팁", "스마트폰 설정", "배터리 절약 방법"],
    "tone": "친절하고 읽기 쉬운 전문 블로거 말투 (~해요, ~입니다)",
    "structure": """
    1. 서론: 독자의 호기심을 유발하는 도입부
    2. 본론 1: 주요 원인 또는 핵심 개념 설명 (소제목 <h2>)
    3. 본론 2: 구체적인 해결 방법 및 단계별 안내 (소제목 <h2> 및 <ul>, <li> 리스트)
    4. 본론 3: 실전 사용 시 주의사항 및 꿀팁 (소제목 <h2>)
    5. 결론: 전체 핵심 요약 및 마무리 인사
    """
}

def get_credentials():
    token_json_str = os.environ.get('BLOGGER_TOKEN_JSON')

    if not token_json_str:
        print("오류: BLOGGER_TOKEN_JSON 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    token_info = json.loads(token_json_str)
    
    # client_secret_json 정보가 있으면 token_info에 추가 반영
    client_secret_json_str = os.environ.get('BLOGGER_CLIENT_SECRET_JSON')
    if client_secret_json_str:
        try:
            client_info = json.loads(client_secret_json_str)
            installed_or_web = client_info.get('installed') or client_info.get('web')
            if installed_or_web:
                if not token_info.get('client_id'):
                    token_info['client_id'] = installed_or_web.get('client_id')
                if not token_info.get('client_secret'):
                    token_info['client_secret'] = installed_or_web.get('client_secret')
        except Exception as e:
            print(f"client_secret 정보 파싱 참고: {e}")

    creds = Credentials.from_authorized_user_info(token_info, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return creds

def generate_blog_post_with_gemini():
    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("경고: GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        today_str = datetime.now().strftime('%Y년 %m월 %d일')
        return {
            "title": f"[{today_str}] 제미나이 API 연동 테스트 포스팅",
            "content": f"<h2>제미나이 API 키 미설정 안내</h2><p>GEMINI_API_KEY 환경변수를 확인해 주세요.</p>",
            "labels": ["테스트", "BloggerAPI"]
        }

    clean_api_key = api_key.strip().strip("'").strip('"')

    keywords_str = ", ".join(BLOG_CONFIG["keywords"])
    prompt = f"""
너는 전문 블로그 콘텐츠 에디터야. 구글 블로그스팟에 포스팅할 높은 품질의 SEO 최적화 글을 작성해줘.

[포스팅 가이드라인]
1. 주제: {BLOG_CONFIG['topic']}
2. 필수 포함 키워드: {keywords_str}
3. 말투/ 어조: {BLOG_CONFIG['tone']}
4. 글 구조:
{BLOG_CONFIG['structure']}

[작성 규칙]
- 검색 엔진(SEO)에 최적화된 매력적인 제목을 지어줘.
- HTML 태그(<h2>, <h3>, <p>, <ul>, <li>, <b>)를 적극 사용해줘.
- 반드시 다른 설명 없이 오직 순수한 JSON 형식으로만 응답해야 해.

[JSON 응답 스키마]
{{
  "title": "블로그 글 제목",
  "content": "<p>HTML 형식의 블로그 본문 내용...</p>",
  "labels": ["태그1", "태그2", "태그3"]
}}
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={clean_api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    response_text = None

    for attempt in range(3):
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            res_json = res.json()

            if res.status_code == 200:
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        response_text = parts[0].get("text", "").strip()
                        print("gemini-2.0-flash 생성 성공!")
                        break
            elif res.status_code == 429:
                print(f"API 요청 한도 대기 중 (429)... 7초 후 재시도 ({attempt+1}/3)")
                time.sleep(7)
            else:
                print(f"HTTP {res.status_code}: {res_json}")
                time.sleep(2)
        except Exception as e:
            print(f"호출 에러: {e}")
            time.sleep(2)

    if not response_text:
        print("Gemini API 대기 한도로 기본 포스팅 양식을 발행합니다.")
        today_str = datetime.now().strftime('%Y년 %m월 %d일')
        return {
            "title": f"[{today_str}] 일일 자동 포스팅",
            "content": f"<h2>일일 자동 포스팅 안내</h2><p>본 포스팅은 자동 예약 시스템을 통해 발행되었습니다.</p>",
            "labels": ["자동포스팅", "일일업데이트"]
        }

    try:
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()

        return json.loads(response_text)
    except Exception as e:
        print(f"Gemini 응답 JSON 파싱 실패: {e}")
        today_str = datetime.now().strftime('%Y년 %m월 %d일')
        return {
            "title": f"[{today_str}] Gemini AI 자동 포스팅",
            "content": f"<div>{response_text}</div>",
            "labels": ["AI포스팅", "Gemini"]
        }

def publish_post(blog_id, title, content, labels=None):
    creds = get_credentials()
    service = build('blogger', 'v3', credentials=creds)

    body = {
        'kind': 'blogger#post',
        'title': title,
        'content': content,
        'labels': labels or []
    }

    request = service.posts().insert(blogId=blog_id, body=body)
    response = request.execute()
    print(f"[성공] 블로그 포스팅 완료!")
    print(f"제목: {response.get('title')}")
    print(f"URL: {response.get('url')}")
    return response

if __name__ == '__main__':
    blog_id = os.environ.get('BLOG_ID', '5571572496232571585')

    print("Gemini AI를 통한 블로그 포스팅 내용 생성 중...")
    post_data = generate_blog_post_with_gemini()

    publish_post(blog_id, post_data.get('title'), post_data.get('content'), post_data.get('labels'))
