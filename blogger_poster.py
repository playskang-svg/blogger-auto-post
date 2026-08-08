import os
import sys
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/blogger']

def get_credentials():
    token_json_str = os.environ.get('BLOGGER_TOKEN_JSON')
    client_secret_json_str = os.environ.get('BLOGGER_CLIENT_SECRET_JSON')

    if not token_json_str:
        print("오류: BLOGGER_TOKEN_JSON 환경변수가 없습니다.")
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
    print(f"[성공] 발행 완료: {response.get('title')}")
    print(f"URL: {response.get('url')}")
    return response

if __name__ == '__main__':
    blog_id = os.environ.get('BLOG_ID', '1709348241841827034')

    # 매일 생성될 포스팅 제목/본문 양식
    today_str = datetime.now().strftime('%Y년 %m월 %d일')
    title = f"[{today_str}] 자동 발행 포스팅"
    content = f"""
    <h2>GitHub Actions 자동 발행 알림</h2>
    <p>본 포스팅은 <b>{today_str}</b>에 자동으로 작성되어 생성된 글입니다.</p>
    """
    labels = ["자동포스팅", "일일업데이트"]

    publish_post(blog_id, title, content, labels)
