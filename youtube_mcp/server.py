# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2,<2", "httpx>=0.27"]
# ///
"""YouTube Data API v3 / YouTube Analytics API용 MCP 서버.

필요한 환경 변수:
  YOUTUBE_API_KEY          공개 데이터 조회용 API 키 (검색, 채널/영상 통계, 댓글)
  YOUTUBE_CLIENT_ID        (선택) 내 채널 분석용 OAuth 클라이언트 ID
  YOUTUBE_CLIENT_SECRET    (선택) OAuth 클라이언트 보안 비밀번호
  YOUTUBE_REFRESH_TOKEN    (선택) get_refresh_token.py로 발급받은 갱신 토큰
"""

import os
import time
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

DATA_URL = "https://www.googleapis.com/youtube/v3"
ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_ANALYTICS_METRICS = [
    "views", "estimatedMinutesWatched", "averageViewDuration",
    "likes", "comments", "shares", "subscribersGained", "subscribersLost",
]

mcp = FastMCP("youtube")

_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0.0}


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _access_token() -> str:
    if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["access_token"]
    names = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    values = [_env(n) for n in names]
    missing = [n for n, v in zip(names, values) if not v]
    if missing:
        raise RuntimeError(f"내 채널 분석에 필요한 환경 변수가 설정되지 않았습니다: {', '.join(missing)}")
    resp = httpx.post(TOKEN_URL, data={
        "client_id": values[0],
        "client_secret": values[1],
        "refresh_token": values[2],
        "grant_type": "refresh_token",
    }, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"구글 토큰 갱신 오류 {resp.status_code}: {resp.text}")
    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + int(data.get("expires_in", 3600))
    return data["access_token"]


def _request(url: str, params: dict | None = None, oauth: bool = False) -> Any:
    params = {k: v for k, v in (params or {}).items() if v is not None}
    headers = {}
    api_key = _env("YOUTUBE_API_KEY")
    if oauth or not api_key:
        if not oauth and not _env("YOUTUBE_REFRESH_TOKEN"):
            raise RuntimeError("환경 변수가 설정되지 않았습니다: YOUTUBE_API_KEY")
        headers["Authorization"] = f"Bearer {_access_token()}"
    else:
        params["key"] = api_key
    resp = httpx.get(url, params=params, headers=headers, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"YouTube API 오류 {resp.status_code}: {resp.text}")
    return resp.json()


def _data(resource: str, params: dict, oauth: bool = False) -> Any:
    return _request(f"{DATA_URL}/{resource}", params, oauth)


@mcp.tool()
def search_videos(
    query: str,
    max_results: int = 10,
    order: str = "relevance",
    region_code: str = "KR",
    published_after: str | None = None,
    channel_id: str | None = None,
) -> Any:
    """키워드로 유튜브 영상을 검색합니다. (호출당 할당량 100 소모)

    order: relevance, date, viewCount, rating
    published_after: RFC 3339 시각 (예: 2026-01-01T00:00:00Z)
    channel_id: 특정 채널 안에서만 검색
    """
    return _data("search", {
        "part": "snippet",
        "type": "video",
        "q": query,
        "maxResults": min(max_results, 50),
        "order": order,
        "regionCode": region_code,
        "relevanceLanguage": "ko" if region_code == "KR" else None,
        "publishedAfter": published_after,
        "channelId": channel_id,
    })


@mcp.tool()
def get_channels(
    channel_ids: list[str] | None = None,
    handle: str | None = None,
    mine: bool = False,
) -> Any:
    """채널 정보와 구독자 수, 총 조회수, 영상 수를 조회합니다.

    channel_ids: UC로 시작하는 채널 ID 목록 (최대 50개)
    handle: @핸들 (예: @naver)
    mine: True면 OAuth로 연결된 내 채널
    """
    params: dict[str, Any] = {"part": "snippet,statistics,contentDetails,brandingSettings"}
    if mine:
        params["mine"] = "true"
    elif handle:
        params["forHandle"] = handle if handle.startswith("@") else f"@{handle}"
    elif channel_ids:
        params["id"] = ",".join(channel_ids[:50])
    else:
        raise ValueError("channel_ids, handle, mine 중 하나는 지정해야 합니다.")
    return _data("channels", params, oauth=mine)


@mcp.tool()
def list_channel_videos(channel_id: str, max_results: int = 20, page_token: str | None = None) -> Any:
    """채널의 최신 업로드 영상 목록을 조회합니다. 통계는 get_videos로 따로 조회하세요."""
    # 채널의 업로드 재생목록 ID는 채널 ID의 UC 접두어를 UU로 바꾼 값입니다.
    playlist_id = "UU" + channel_id[2:] if channel_id.startswith("UC") else channel_id
    return _data("playlistItems", {
        "part": "snippet,contentDetails",
        "playlistId": playlist_id,
        "maxResults": min(max_results, 50),
        "pageToken": page_token,
    })


@mcp.tool()
def get_videos(video_ids: list[str]) -> Any:
    """영상의 제목, 길이, 조회수, 좋아요 수, 댓글 수 등을 조회합니다. (최대 50개)"""
    return _data("videos", {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(video_ids[:50]),
    })


@mcp.tool()
def get_popular_videos(region_code: str = "KR", category_id: str | None = None, max_results: int = 20) -> Any:
    """국가별 인기 급상승 영상을 조회합니다. category_id 예: 10(음악), 20(게임), 22(인물/블로그), 24(엔터테인먼트)"""
    return _data("videos", {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "videoCategoryId": category_id,
        "maxResults": min(max_results, 50),
    })


@mcp.tool()
def list_comments(
    video_id: str,
    max_results: int = 20,
    order: str = "relevance",
    page_token: str | None = None,
) -> Any:
    """영상의 댓글(최상위 댓글과 일부 답글)을 조회합니다. order: relevance 또는 time"""
    return _data("commentThreads", {
        "part": "snippet,replies",
        "videoId": video_id,
        "maxResults": min(max_results, 100),
        "order": order,
        "textFormat": "plainText",
        "pageToken": page_token,
    })


@mcp.tool()
def get_channel_analytics(
    start_date: str,
    end_date: str,
    metrics: list[str] | None = None,
    dimensions: list[str] | None = None,
    filters: str | None = None,
    sort: str | None = None,
    max_results: int | None = None,
) -> Any:
    """[OAuth 필요] 내 채널의 YouTube 애널리틱스 보고서를 조회합니다.

    start_date/end_date: 'YYYY-MM-DD'
    metrics: 기본값 views, estimatedMinutesWatched, averageViewDuration, likes, comments,
      shares, subscribersGained, subscribersLost
    dimensions: 예) ['day'], ['video'], ['country'], ['insightTrafficSourceType'],
      ['ageGroup','gender'] (ageGroup/gender는 metrics=['viewerPercentage']와 함께)
    filters: 예) 'video==VIDEO_ID', 'country==KR'
    sort: 예) '-views' (dimensions=['video']일 때는 sort와 max_results 필수)
    """
    return _request(ANALYTICS_URL, {
        "ids": "channel==MINE",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": ",".join(metrics or DEFAULT_ANALYTICS_METRICS),
        "dimensions": ",".join(dimensions) if dimensions else None,
        "filters": filters,
        "sort": sort,
        "maxResults": max_results,
    }, oauth=True)


if __name__ == "__main__":
    mcp.run()
