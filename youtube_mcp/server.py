# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2,<2", "httpx>=0.27"]
# ///
"""YouTube Data API / YouTube Analytics API용 MCP 서버.

공개 데이터 (영상, 채널, 검색, 댓글):
  YOUTUBE_API_KEY                 Google Cloud 콘솔에서 발급한 API 키

내 채널 분석 데이터 (조회수 추이, 시청 시간, 유입 경로, 시청자층 등):
  YOUTUBE_OAUTH_CLIENT_ID         OAuth 클라이언트 ID (데스크톱 앱 유형)
  YOUTUBE_OAUTH_CLIENT_SECRET     OAuth 클라이언트 보안 비밀번호
  YOUTUBE_OAUTH_REFRESH_TOKEN     get_refresh_token.py로 발급한 리프레시 토큰
"""

import datetime
import os
import time
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

DATA_URL = "https://www.googleapis.com/youtube/v3"
ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"
TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_REPORT_METRICS = [
    "views", "estimatedMinutesWatched", "averageViewDuration", "averageViewPercentage",
    "likes", "comments", "shares", "subscribersGained", "subscribersLost",
]

mcp = FastMCP("youtube")
_token: dict[str, Any] = {"value": None, "expires_at": 0.0}


def _env(*names: str) -> list[str]:
    values = [os.environ.get(n, "").strip() for n in names]
    missing = [n for n, v in zip(names, values) if not v]
    if missing:
        raise RuntimeError(f"환경 변수가 설정되지 않았습니다: {', '.join(missing)}")
    return values


def _access_token() -> str:
    if _token["value"] and time.time() < _token["expires_at"] - 60:
        return _token["value"]
    client_id, client_secret, refresh_token = _env(
        "YOUTUBE_OAUTH_CLIENT_ID", "YOUTUBE_OAUTH_CLIENT_SECRET", "YOUTUBE_OAUTH_REFRESH_TOKEN"
    )
    resp = httpx.post(TOKEN_URL, data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"OAuth 토큰 갱신 실패 {resp.status_code}: {resp.text}")
    data = resp.json()
    _token["value"] = data["access_token"]
    _token["expires_at"] = time.time() + data.get("expires_in", 3600)
    return _token["value"]


def _request(url: str, params: dict, oauth: bool = False) -> Any:
    params = {k: v for k, v in params.items() if v is not None}
    # 키를 URL이 아닌 헤더로 보내야 요청 로그에 키가 남지 않습니다.
    if oauth:
        headers = {"Authorization": f"Bearer {_access_token()}"}
    else:
        headers = {"X-Goog-Api-Key": _env("YOUTUBE_API_KEY")[0]}
    resp = httpx.get(url, params=params, headers=headers, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"YouTube API 오류 {resp.status_code}: {resp.text}")
    return resp.json()


def _data(path: str, params: dict, oauth: bool = False) -> Any:
    return _request(DATA_URL + path, params, oauth)


def _date_range(start_date: str | None, end_date: str | None, days: int) -> tuple[str, str]:
    end = end_date or datetime.date.today().isoformat()
    start = start_date or (datetime.date.fromisoformat(end) - datetime.timedelta(days=days - 1)).isoformat()
    return start, end


def _rows(report: dict) -> list[dict]:
    """Analytics 응답의 columnHeaders/rows를 읽기 쉬운 dict 목록으로 바꿉니다."""
    names = [h["name"] for h in report.get("columnHeaders", [])]
    return [dict(zip(names, row)) for row in report.get("rows", [])]


# ---------- 공개 데이터 (API 키) ----------

@mcp.tool()
def search(
    query: str,
    type: str = "video",
    max_results: int = 10,
    order: str = "relevance",
    region_code: str | None = "KR",
    published_after: str | None = None,
    channel_id: str | None = None,
) -> Any:
    """YouTube에서 영상/채널/재생목록을 검색합니다. 할당량을 100 단위 쓰므로 꼭 필요할 때만 사용하세요.

    type: video, channel, playlist
    order: relevance, date, viewCount, rating
    published_after: 'YYYY-MM-DD' 이후 게시물만
    channel_id: 특정 채널 안에서만 검색
    """
    after = f"{published_after}T00:00:00Z" if published_after else None
    return _data("/search", {
        "part": "snippet", "q": query, "type": type, "maxResults": min(max_results, 50),
        "order": order, "regionCode": region_code, "publishedAfter": after, "channelId": channel_id,
    })


@mcp.tool()
def get_channels(channel_ids: list[str] | None = None, handle: str | None = None) -> Any:
    """채널 정보(구독자 수, 총 조회수, 영상 수, 업로드 재생목록 ID 등)를 조회합니다.

    channel_ids: UC로 시작하는 채널 ID 목록 (최대 50개)
    handle: '@핸들' 형식의 채널 핸들 (channel_ids 대신 사용)
    """
    return _data("/channels", {
        "part": "snippet,statistics,contentDetails,brandingSettings",
        "id": ",".join(channel_ids) if channel_ids else None,
        "forHandle": handle,
    })


@mcp.tool()
def get_videos(video_ids: list[str]) -> Any:
    """영상의 제목, 게시일, 길이, 조회수, 좋아요, 댓글 수, 태그를 조회합니다. (최대 50개)"""
    return _data("/videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(video_ids[:50])})


@mcp.tool()
def list_channel_videos(channel_id: str, max_results: int = 25, page_token: str | None = None) -> Any:
    """채널의 최근 업로드 영상 목록을 최신순으로 조회합니다. 조회수 등은 get_videos로 이어서 조회하세요."""
    uploads = "UU" + channel_id[2:] if channel_id.startswith("UC") else channel_id
    return _data("/playlistItems", {
        "part": "snippet,contentDetails", "playlistId": uploads,
        "maxResults": min(max_results, 50), "pageToken": page_token,
    })


@mcp.tool()
def list_comments(video_id: str, max_results: int = 20, order: str = "relevance") -> Any:
    """영상의 댓글(최상위 댓글)을 조회합니다. order: relevance(인기순), time(최신순)"""
    return _data("/commentThreads", {
        "part": "snippet", "videoId": video_id, "maxResults": min(max_results, 100),
        "order": order, "textFormat": "plainText",
    })


# ---------- 내 채널 분석 데이터 (OAuth) ----------

@mcp.tool()
def get_my_channel() -> Any:
    """OAuth로 연결된 내 채널의 기본 정보와 통계를 조회합니다."""
    return _data("/channels", {"part": "snippet,statistics,contentDetails", "mine": "true"}, oauth=True)


@mcp.tool()
def analytics_report(
    metrics: list[str] | None = None,
    dimensions: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    filters: str | None = None,
    sort: str | None = None,
    max_results: int | None = None,
) -> Any:
    """내 채널의 YouTube Analytics 보고서를 조회합니다. 기간 기본값은 최근 28일입니다.

    metrics: 기본값 views, estimatedMinutesWatched, averageViewDuration, averageViewPercentage,
      likes, comments, shares, subscribersGained, subscribersLost
      (수익: estimatedRevenue — 수익 권한으로 토큰을 발급한 경우만)
    dimensions 예시:
      day / month                 기간별 추이
      video                       영상별 (sort='-views', max_results 필요)
      insightTrafficSourceType    유입 경로 (검색, 추천, 외부 등)
      ageGroup,gender             시청자 연령/성별 (metrics=['viewerPercentage'])
      country                     국가별
      deviceType                  기기별
      subscribedStatus            구독자/비구독자
      creatorContentType          쇼츠/일반 영상/라이브 구분
    filters 예시: 'video==영상ID', 'country==KR', 'insightTrafficSourceType==YT_SEARCH'
    sort 예시: '-views' (내림차순), 'day'
    """
    start, end = _date_range(start_date, end_date, 28)
    report = _request(ANALYTICS_URL, {
        "ids": "channel==MINE",
        "startDate": start,
        "endDate": end,
        "metrics": ",".join(metrics or DEFAULT_REPORT_METRICS),
        "dimensions": ",".join(dimensions) if dimensions else None,
        "filters": filters,
        "sort": sort,
        "maxResults": max_results,
    }, oauth=True)
    return {"startDate": start, "endDate": end, "rows": _rows(report)}


@mcp.tool()
def top_videos(
    start_date: str | None = None,
    end_date: str | None = None,
    max_results: int = 10,
    sort_by: str = "views",
) -> Any:
    """기간 내 성과가 좋은 내 영상 순위를 제목과 함께 조회합니다. 기간 기본값은 최근 28일입니다.

    sort_by: views, estimatedMinutesWatched, subscribersGained, likes, shares
    """
    result = analytics_report(
        metrics=["views", "estimatedMinutesWatched", "averageViewDuration",
                 "averageViewPercentage", "likes", "shares", "subscribersGained"],
        dimensions=["video"], start_date=start_date, end_date=end_date,
        sort=f"-{sort_by}", max_results=min(max_results, 200),
    )
    ids = [r["video"] for r in result["rows"]][:50]
    if ids:
        info = _data("/videos", {"part": "snippet", "id": ",".join(ids)}, oauth=True)
        titles = {v["id"]: v["snippet"] for v in info.get("items", [])}
        for row in result["rows"]:
            snippet = titles.get(row["video"], {})
            row["title"] = snippet.get("title")
            row["publishedAt"] = snippet.get("publishedAt")
    return result


if __name__ == "__main__":
    mcp.run()
