# 유튜브 MCP 서버

Claude가 YouTube Data API와 YouTube Analytics API로 영상 검색, 채널/영상 통계, 댓글, 내 채널 분석 데이터를 조회할 수 있게 해 주는 연결 프로그램입니다.
저장소 루트의 `.mcp.json`에 등록되어 있어서, 이 저장소에서 Claude Code를 열면 자동으로 연결됩니다. 모든 기능은 **조회 전용**이며 채널이나 영상을 바꾸지 않습니다.

## 준비물

### 1. 공개 데이터용 API 키 (필수)

1. [Google Cloud 콘솔](https://console.cloud.google.com/)에서 프로젝트를 만듭니다.
2. API 및 서비스 → 라이브러리에서 **YouTube Data API v3**를 사용 설정합니다.
3. API 및 서비스 → 사용자 인증 정보 → **API 키 만들기**. 키 제한에서 YouTube Data API v3만 허용해 두는 것을 권장합니다.
4. 환경 변수로 넣습니다.
   ```
   YOUTUBE_API_KEY=발급받은 API 키
   ```

### 2. 내 채널 분석용 OAuth (선택)

`get_channel_analytics`와 `get_channels(mine=True)`를 쓰려면 필요합니다.

1. 같은 프로젝트에서 **YouTube Analytics API**도 사용 설정합니다.
2. OAuth 동의 화면을 설정하고(외부, 테스트 사용자에 내 구글 계정 추가), 사용자 인증 정보 → **OAuth 클라이언트 ID** → 애플리케이션 유형 **데스크톱 앱**으로 만듭니다.
3. 브라우저가 있는 내 컴퓨터에서 아래를 실행하고, 채널 소유 계정으로 로그인해 허용합니다.
   ```
   YOUTUBE_CLIENT_ID=... YOUTUBE_CLIENT_SECRET=... uv run --script youtube_mcp/get_refresh_token.py
   ```
4. 출력된 값과 함께 세 개를 환경 변수로 넣습니다.
   ```
   YOUTUBE_CLIENT_ID=OAuth 클라이언트 ID
   YOUTUBE_CLIENT_SECRET=OAuth 클라이언트 보안 비밀번호
   YOUTUBE_REFRESH_TOKEN=스크립트가 출력한 값
   ```
   동의 화면이 "테스트" 상태면 갱신 토큰이 7일 뒤 만료되니, 계속 쓰려면 동의 화면을 "프로덕션"으로 게시하세요.

키와 토큰은 비밀번호와 같으니 저장소 파일이나 채팅창에 넣지 마세요. 클라우드 환경이라면 환경 설정 화면의 환경 변수 칸에 넣으면 됩니다.

### 3. 네트워크

네트워크 허용 도메인에 `www.googleapis.com`, `youtubeanalytics.googleapis.com`, `oauth2.googleapis.com`이 있어야 합니다.

## 제공 기능

| 도구 | 설명 | 인증 |
| --- | --- | --- |
| `search_videos` | 키워드로 영상 검색 (정렬, 기간, 채널 필터) | API 키 |
| `get_channels` | 채널 정보, 구독자/조회수/영상 수 (ID, @핸들, 내 채널) | API 키 / 내 채널은 OAuth |
| `list_channel_videos` | 채널의 최신 업로드 목록 | API 키 |
| `get_videos` | 영상별 조회수, 좋아요, 댓글 수, 길이 | API 키 |
| `get_popular_videos` | 국가별 인기 급상승 영상 | API 키 |
| `list_comments` | 영상 댓글 | API 키 |
| `get_channel_analytics` | 내 채널 시청 시간, 유입 경로, 시청자 연령/성별/국가 등 | OAuth |

## 할당량

YouTube Data API는 프로젝트당 하루 10,000 단위가 기본입니다. `search_videos`는 한 번에 100 단위, 나머지 조회는 대부분 1 단위를 씁니다.

## 직접 실행

```
uv run --script youtube_mcp/server.py
```
