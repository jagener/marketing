# 네이버 검색광고 MCP 서버

Claude가 네이버 검색광고 API로 캠페인, 키워드, 성과 데이터를 조회하고 입찰가를 바꿀 수 있게 해 주는 연결 프로그램입니다.
저장소 루트의 `.mcp.json`에 등록되어 있어서, 이 저장소에서 Claude Code를 열면 자동으로 연결됩니다.

## 준비물

1. 검색광고 관리시스템(searchad.naver.com) → 도구 → **API 사용 관리**에서 키를 발급받습니다.
2. 발급받은 값을 환경 변수로 넣습니다. 클라우드 환경이라면 환경 설정 화면의 환경 변수 칸에 넣으면 됩니다.
   ```
   NAVER_SEARCHAD_API_KEY=액세스 라이선스
   NAVER_SEARCHAD_SECRET_KEY=비밀키
   NAVER_SEARCHAD_CUSTOMER_ID=CUSTOMER_ID
   ```
   키는 비밀번호와 같으니 저장소 파일이나 채팅창에 넣지 마세요.
3. 네트워크 허용 도메인에 `api.searchad.naver.com`이 있어야 합니다.

## 제공 기능

| 도구 | 설명 |
| --- | --- |
| `get_bizmoney` | 비즈머니 잔액 |
| `list_campaigns` | 캠페인 목록 |
| `list_adgroups` | 광고그룹 목록 (캠페인별 필터 가능) |
| `list_keywords` | 광고그룹의 키워드와 입찰가 |
| `list_ads` | 광고그룹의 소재 |
| `get_stats` | 노출, 클릭, 비용, 전환 등 성과 (기간 또는 일별) |
| `keyword_tool` | 연관 키워드와 월간 검색수 |
| `update_keyword_bid` | **실제 변경**: 키워드 입찰가 변경 |
| `set_campaign_paused` | **실제 변경**: 캠페인 일시중지/재개 |

## 직접 실행

```
uv run --script naver_searchad_mcp/server.py
```
