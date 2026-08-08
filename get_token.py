import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/blogger']

def main():
    if not os.path.exists('client_secret.json'):
        print("오류: client_secret.json 파일이 필요합니다.")
        return

    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
    creds = flow.run_local_server(port=0)

    with open('token.json', 'w', encoding='utf-8') as f:
        f.write(creds.to_json())

    print("[성공] token.json이 생성되었습니다!")

if __name__ == '__main__':
    main()
