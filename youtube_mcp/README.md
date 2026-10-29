# YouTube MCP 서버

Claude가 YouTube 데이터를 조회할 수 있게 해 주는 연결 프로그램입니다. 공개 데이터(영상, 채널, 검색, 댓글)와 **내 채널 분석 데이터**(조회수 추이, 시청 시간, 유입 경로, 시청자층)를 볼 수 있습니다.
저장소 루트의 `.mcp.json`에 등록되어 있어서, 이 저장소에서 Claude Code를 열면 자동으로 연결됩니다. 모든 도구는 조회만 하고, 채널이나 영상을 바꾸지 않습니다.

## 1. 공개 데이터: API 키

Google Cloud 콘솔 → API 및 서비스 → **사용자 인증 정보**에서 API 키를 만들고, **YouTube Data API v3**를 사용 설정합니다.

```
YOUTUBE_API_KEY=API 키
```

## 2. 내 채널 분석 데이터: OAuth

API 키로는 남의 채널처럼 공개된 숫자만 보입니다. 시청 시간, 유입 경로, 시청자층 같은 데이터는 채널 주인의 Google 로그인 승인이 필요합니다. 처음 한 번만 하면 됩니다.

1. **API 사용 설정**: API 키와 같은 Google Cloud 프로젝트에서 **YouTube Analytics API**도 사용 설정합니다.
2. **OAuth 동의 화면**: API 및 서비스 → OAuth 동의 화면에서 사용자 유형을 **외부**로 만들고, 테스트 사용자에 채널 주인의 Google 계정을 추가합니다.
   - 게시 상태가 "테스트"이면 리프레시 토큰이 7일 뒤 만료됩니다. 계속 쓰려면 **앱 게시**를 눌러 "프로덕션"으로 바꾸세요. 개인용이라 Google 심사를 받지 않아도 되고, 로그인 때 "확인되지 않은 앱" 경고가 나오면 고급 → 계속을 누르면 됩니다.
3. **OAuth 클라이언트**: 사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID → 애플리케이션 유형 **데스크톱 앱**. 클라이언트 ID와 보안 비밀번호를 받아 둡니다.
4. **리프레시 토큰 발급**: 브라우저가 있는 내 컴퓨터에서 저장소를 받은 뒤 실행합니다 (파이썬 3만 있으면 됩니다).
   ```
   python youtube_mcp/get_refresh_token.py
   ```
   수익(`estimatedRevenue`)도 보려면 `--revenue`를 붙입니다. 브랜드 계정 채널이라면 로그인 화면에서 그 채널을 고르세요.
5. **환경 변수 등록**:
   ```
   YOUTUBE_OAUTH_CLIENT_ID=클라이언트 ID
   YOUTUBE_OAUTH_CLIENT_SECRET=클라이언트 보안 비밀번호
   YOUTUBE_OAUTH_REFRESH_TOKEN=4단계에서 받은 토큰
   ```

키와 토큰은 비밀번호와 같으니 저장소 파일이나 채팅창에 넣지 마세요. 클라우드 환경이라면 환경 설정 화면의 환경 변수 칸에 넣으면 되고, 새 세션부터 적용됩니다.
네트워크 허용 도메인에 `www.googleapis.com`, `youtubeanalytics.googleapis.com`, `oauth2.googleapis.com`이 있어야 합니다.

## 제공 기능

| 도구 | 인증 | 설명 |
| --- | --- | --- |
| `search` | API 키 | 영상/채널/재생목록 검색 (할당량 100 단위 소모) |
| `get_channels` | API 키 | 채널 구독자 수, 총 조회수, 영상 수 (ID 또는 @핸들) |
| `get_videos` | API 키 | 영상 조회수, 좋아요, 댓글 수, 길이, 태그 |
| `list_channel_videos` | API 키 | 채널의 최근 업로드 목록 |
| `list_comments` | API 키 | 영상 댓글 |
| `get_my_channel` | OAuth | 내 채널 기본 정보 |
| `analytics_report` | OAuth | 내 채널 분석 보고서 (기간별, 영상별, 유입 경로, 연령/성별, 국가, 기기, 쇼츠 구분 등) |
| `top_videos` | OAuth | 기간 내 성과 상위 영상 (제목 포함) |

YouTube Data API는 하루 10,000 단위 할당량이 있습니다. 대부분의 조회는 1 단위, `search`만 100 단위입니다.

## 직접 실행

```
uv run --script youtube_mcp/server.py
```
