import os
import sys
import json
from datetime import datetime
import anthropic
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/blogger']

def get_credentials():
    token_json_str = os.environ.get('BLOGGER_TOKEN_JSON')
    client_secret_json_str = os.environ.get('BLOGGER_CLIENT_SECRET_JSON')

    if not token_json_str:
        print("오류: BLOGGER_TOKEN_JSON 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    token_info = json.loads(token_json_str)
    creds = Credentials.from_authorized_user_info(token_info, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        if client_secret_json_str:
            client_info = json.loads(client_secret_json_str)
            installed_or_web = client_info.get('installed') or client_info.get('web')
            if installed_or_web:
                creds.client_id = installed_or_web.get('client_id')
                creds.client_secret = installed_or_web.get('client_secret')
                creds.token_uri = installed_or_web.get('token_uri', 'https://oauth2.googleapis.com/token')

        creds.refresh(Request())

    return creds

def generate_blog_post_with_claude():
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("경고: ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        today_str = datetime.now().strftime('%Y년 %m월 %d일')
        return {
            "title": f"[{today_str}] 클로드 API 연동 테스트 포스팅",
            "content": f"<h2>클로드 API 키 미설정 안내</h2><p>ANTHROPIC_API_KEY 환경변수를 확인해 주세요.</p>",
            "labels": ["테스트", "BloggerAPI"]
        }

    client = anthropic.Anthropic(api_key=api_key)

    prompt = """
너는 전문 블로그 콘텐츠 에디터야. 구글 블로그스팟에 포스팅할 높은 품질의 SEO 최적화 글을 작성해줘.

[요구사항]
1. 주제: 최근 트렌드, 유용한 생활 팁, IT 기술, 또는 금융/경제 관련 정보 중 하나를 자유롭게 선택하여 흥미롭고 알찬 글을 써줘.
2. 구성:
   - 가독성이 좋은 소제목(<h2>, <h3>)과 깔끔한 문단(<p>), 리스트(<ul>, <li>) 등의 HTML 태그를 활용해줘.
   - 서론-본론-결론 구조로 작성해줘.
3. 출력 형식:
   다른 설명 없이 오직 순수한 JSON 형식으로만 응답해야 해.

[JSON 응답 스키마]
{
  "title": "블로그 글 제목",
  "content": "<p>HTML 형식의 블로그 본문 내용...</p>",
  "labels": ["태그1", "태그2", "태그3"]
}
"""

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2500,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response.content[0].text.strip()

    # JSON 응답 파싱
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
        print(f"Claude 응답 JSON 파싱 실패: {e}")
        today_str = datetime.now().strftime('%Y년 %m월 %d일')
        return {
            "title": f"[{today_str}] Claude AI 자동 포스팅",
            "content": f"<div>{response_text}</div>",
            "labels": ["AI포스팅", "Claude"]
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
    blog_id = os.environ.get('BLOG_ID', '1709348241841827034')

    print("Claude AI를 통한 블로그 포스팅 생성 중...")
    post_data = generate_blog_post_with_claude()

    publish_post(blog_id, post_data.get('title'), post_data.get('content'), post_data.get('labels'))
