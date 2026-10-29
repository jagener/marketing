"""내 채널 분석 데이터용 OAuth 리프레시 토큰을 발급합니다. 브라우저가 있는 내 컴퓨터에서 실행하세요.

사용법:
  python youtube_mcp/get_refresh_token.py              # 기본 권한 (채널 정보, 분석 데이터)
  python youtube_mcp/get_refresh_token.py --revenue    # 수익(estimatedRevenue) 조회 권한까지

실행하면 클라이언트 ID와 보안 비밀번호를 묻고, 브라우저에서 Google 로그인 후
리프레시 토큰을 화면에 출력합니다. 외부 패키지 없이 파이썬 표준 라이브러리만 씁니다.
"""

import getpass
import hashlib
import base64
import http.server
import json
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
REVENUE_SCOPE = "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"


def main() -> None:
    scopes = SCOPES + ([REVENUE_SCOPE] if "--revenue" in sys.argv else [])
    client_id = input("OAuth 클라이언트 ID: ").strip()
    client_secret = getpass.getpass("OAuth 클라이언트 보안 비밀번호 (입력이 보이지 않습니다): ").strip()

    result: dict[str, str] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in query.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("인증이 끝났습니다. 이 창을 닫고 터미널로 돌아가세요.".encode())

        def log_message(self, *args) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect_uri = f"http://127.0.0.1:{server.server_port}"
    state = secrets.token_urlsafe(16)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()

    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    print("\n브라우저에서 Google 로그인 화면을 엽니다. 열리지 않으면 아래 주소를 직접 여세요:\n" + url + "\n")
    webbrowser.open(url)
    while "code" not in result and "error" not in result:
        server.handle_request()

    if "error" in result:
        sys.exit(f"인증 실패: {result['error']}")
    if result.get("state") != state:
        sys.exit("인증 실패: state 값이 맞지 않습니다. 다시 실행하세요.")

    body = urllib.parse.urlencode({
        "code": result["code"],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": verifier,
    }).encode()
    with urllib.request.urlopen(TOKEN_URL, data=body) as resp:
        token = json.load(resp)

    if "refresh_token" not in token:
        sys.exit("리프레시 토큰이 오지 않았습니다. https://myaccount.google.com/permissions 에서 앱 권한을 지운 뒤 다시 실행하세요.")
    print("발급 완료. 아래 값을 환경 변수 YOUTUBE_OAUTH_REFRESH_TOKEN 에 넣으세요 (채팅창에는 붙여넣지 마세요):\n")
    print(token["refresh_token"])


if __name__ == "__main__":
    main()
