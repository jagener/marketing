# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2,<2", "httpx>=0.27"]
# ///
"""네이버 검색광고 API용 MCP 서버.

필요한 환경 변수 (검색광고 관리시스템 > 도구 > API 사용 관리에서 발급):
  NAVER_SEARCHAD_API_KEY      액세스 라이선스
  NAVER_SEARCHAD_SECRET_KEY   비밀키
  NAVER_SEARCHAD_CUSTOMER_ID  CUSTOMER_ID
"""

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = "https://api.searchad.naver.com"
DEFAULT_STAT_FIELDS = ["impCnt", "clkCnt", "salesAmt", "ctr", "cpc", "avgRnk", "ccnt", "crto", "convAmt"]

mcp = FastMCP("naver-searchad")


def _credentials() -> tuple[str, str, str]:
    names = ("NAVER_SEARCHAD_API_KEY", "NAVER_SEARCHAD_SECRET_KEY", "NAVER_SEARCHAD_CUSTOMER_ID")
    values = [os.environ.get(n, "").strip() for n in names]
    missing = [n for n, v in zip(names, values) if not v]
    if missing:
        raise RuntimeError(f"환경 변수가 설정되지 않았습니다: {', '.join(missing)}")
    return values[0], values[1], values[2]


def sign(timestamp: str, method: str, uri: str, secret_key: str) -> str:
    message = f"{timestamp}.{method}.{uri}"
    digest = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _request(method: str, uri: str, params: dict | None = None, body: Any = None) -> Any:
    api_key, secret_key, customer_id = _credentials()
    timestamp = str(int(time.time() * 1000))
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": customer_id,
        "X-Signature": sign(timestamp, method, uri, secret_key),
    }
    params = {k: v for k, v in (params or {}).items() if v is not None}
    resp = httpx.request(method, BASE_URL + uri, params=params, json=body, headers=headers, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"네이버 API 오류 {resp.status_code}: {resp.text}")
    return resp.json() if resp.content else {"status": resp.status_code}


@mcp.tool()
def get_bizmoney() -> Any:
    """비즈머니(광고 충전금) 잔액을 조회합니다."""
    return _request("GET", "/billing/bizmoney")


@mcp.tool()
def list_campaigns() -> Any:
    """광고 계정의 모든 캠페인 목록을 조회합니다."""
    return _request("GET", "/ncc/campaigns")


@mcp.tool()
def list_adgroups(campaign_id: str | None = None) -> Any:
    """광고그룹 목록을 조회합니다. campaign_id(nccCampaignId)를 주면 해당 캠페인의 광고그룹만 조회합니다."""
    return _request("GET", "/ncc/adgroups", {"nccCampaignId": campaign_id})


@mcp.tool()
def list_keywords(adgroup_id: str) -> Any:
    """광고그룹(nccAdgroupId)에 등록된 키워드와 입찰가를 조회합니다."""
    return _request("GET", "/ncc/keywords", {"nccAdgroupId": adgroup_id})


@mcp.tool()
def list_ads(adgroup_id: str) -> Any:
    """광고그룹(nccAdgroupId)에 등록된 광고 소재를 조회합니다."""
    return _request("GET", "/ncc/ads", {"nccAdgroupId": adgroup_id})


@mcp.tool()
def get_stats(
    ids: list[str],
    since: str | None = None,
    until: str | None = None,
    date_preset: str | None = None,
    fields: list[str] | None = None,
    daily: bool = False,
) -> Any:
    """캠페인/광고그룹/키워드/소재 ID의 성과(노출, 클릭, 비용, 전환 등)를 조회합니다.

    ids: 조회할 ID 목록 (예: cmp-..., grp-..., nkw-...)
    since/until: 'YYYY-MM-DD' 기간. 또는 date_preset 사용
      (today, yesterday, last7days, last30days, lastweek, lastmonth 등)
    fields: 기본값 impCnt, clkCnt, salesAmt(비용), ctr, cpc, avgRnk, ccnt(전환수), crto(전환율), convAmt(전환매출)
    daily: True면 일별로 나눠서 반환
    """
    params: dict[str, Any] = {
        "ids": ",".join(ids),
        "fields": json.dumps(fields or DEFAULT_STAT_FIELDS),
        "timeIncrement": "1" if daily else "allDays",
    }
    if since and until:
        params["timeRange"] = json.dumps({"since": since, "until": until})
    else:
        params["datePreset"] = date_preset or "last7days"
    return _request("GET", "/stats", params)


@mcp.tool()
def keyword_tool(hint_keywords: list[str]) -> Any:
    """연관 키워드와 월간 검색수(PC/모바일), 경쟁 정도를 조회합니다. 키워드는 최대 5개, 공백은 제거됩니다."""
    hints = ",".join(k.replace(" ", "") for k in hint_keywords[:5])
    return _request("GET", "/keywordstool", {"hintKeywords": hints, "showDetail": "1"})


@mcp.tool()
def update_keyword_bid(keyword_id: str, adgroup_id: str, bid_amount: int) -> Any:
    """[실제 광고 변경] 키워드(nccKeywordId)의 입찰가를 원 단위로 변경합니다. 광고비에 바로 영향을 줍니다."""
    body = {
        "nccKeywordId": keyword_id,
        "nccAdgroupId": adgroup_id,
        "bidAmt": bid_amount,
        "useGroupBidAmt": False,
    }
    return _request("PUT", f"/ncc/keywords/{keyword_id}", {"fields": "bidAmt"}, body)


@mcp.tool()
def set_campaign_paused(campaign_id: str, paused: bool) -> Any:
    """[실제 광고 변경] 캠페인을 일시중지(paused=True)하거나 다시 켭니다(paused=False)."""
    body = {"nccCampaignId": campaign_id, "userLock": paused}
    return _request("PUT", f"/ncc/campaigns/{campaign_id}", {"fields": "userLock"}, body)


if __name__ == "__main__":
    mcp.run()
