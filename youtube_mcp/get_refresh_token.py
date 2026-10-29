# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27"]
# ///
"""내 채널 분석용 YOUTUBE_REFRESH_TOKEN을 발급받는 1회용 스크립트.

브라우저가 있는 내 컴퓨터에서 실행하세요:
  YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... uv run --script youtube_mcp/get_refresh_token.py
"""

import http.server
import os
import secrets
import urllib.parse
import webbrowser

import httpx

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
PORT = 8765
REDIRECT_URI = f"http://127.0.0.1:{PORT}"


def main() -> None:
    client_id = os.environ["YOUTUBE_CLIENT_ID"].strip()
    client_secret = os.environ["YOUTUBE_CLIENT_SECRET"].strip()
    state = secrets.token_urlsafe(16)
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })
    result: dict[str, str] = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if query.get("state", [""])[0] == state and "code" in query:
                result["code"] = query["code"][0]
                message = "인증이 끝났습니다. 이 창을 닫고 터미널로 돌아가세요."
            else:
                message = "인증에 실패했습니다: " + query.get("error", ["알 수 없는 오류"])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(message.encode())

        def log_message(self, *args) -> None:
            pass

    print("브라우저에서 구글 계정으로 로그인하고 권한을 허용하세요:\n" + auth_url)
    webbrowser.open(auth_url)
    with http.server.HTTPServer(("127.0.0.1", PORT), Handler) as server:
        while "code" not in result:
            server.handle_request()

    resp = httpx.post("https://oauth2.googleapis.com/token", data={
        "code": result["code"],
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }, timeout=30)
    resp.raise_for_status()
    print("\nYOUTUBE_REFRESH_TOKEN=" + resp.json()["refresh_token"])


if __name__ == "__main__":
    main()
