import json
import os
import time
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

CONTROL_FILE = Path(
    os.getenv(
        "BOOKMARK_ATLAS_CONTROL_FILE",
        str(BASE_DIR / "control.json"),
    )
)
CONTROL_FILE_DISABLED = os.getenv("BOOKMARK_ATLAS_DISABLE_CONTROL_FILE", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

DEFAULT_COOKIES = {
    "auth_token":           "",
    "ct0":                  "",
    "twid":                 "",
    "guest_id":             "",
    "guest_id_ads":         "",
    "guest_id_marketing":   "",
    "personalization_id":   "",
    "kdt":                  "",
    "__cuid":               "",
    "lang":                 "en",
}

# ✅ Current working query ID (from your browser DevTools)
DEFAULT_QUERY_ID = "mGNnajwr-hIsOQEb1myr0g"

DEFAULT_BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

# ✅ Exact features from your curl request
FEATURES = json.dumps({
    "rweb_video_screen_enabled": False,
    "rweb_cashtags_enabled": True,
    "profile_label_improvements_pcf_label_in_post_enabled": True,
    "responsive_web_profile_redirect_enabled": False,
    "rweb_tipjar_consumption_enabled": False,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "premium_content_api_read_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
    "responsive_web_grok_analyze_post_followups_enabled": True,
    "responsive_web_jetfuel_frame": True,
    "responsive_web_grok_share_attachment_enabled": True,
    "responsive_web_grok_annotations_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "content_disclosure_indicator_enabled": True,
    "content_disclosure_ai_generated_indicator_enabled": True,
    "responsive_web_grok_show_grok_translated_post": True,
    "responsive_web_grok_analysis_button_from_backend": True,
    "post_ctas_fetch_enabled": True,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": False,
    "responsive_web_grok_image_annotation_enabled": True,
    "responsive_web_grok_imagine_annotation_enabled": True,
    "responsive_web_grok_community_note_auto_translation_is_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}, separators=(',', ':'))


COOKIE_ENV_MAP = {
    "auth_token": "X_AUTH_TOKEN",
    "ct0": "X_CT0",
    "twid": "X_TWID",
    "guest_id": "X_GUEST_ID",
    "guest_id_ads": "X_GUEST_ID_ADS",
    "guest_id_marketing": "X_GUEST_ID_MARKETING",
    "personalization_id": "X_PERSONALIZATION_ID",
    "kdt": "X_KDT",
    "__cuid": "X_CUID",
    "lang": "X_LANG",
}


def get_env_account_config():
    return {
        "account_key": os.getenv("X_ACCOUNT_KEY", ""),
        "owner_username": os.getenv("X_OWNER_USERNAME", ""),
        "auth_token": os.getenv("X_AUTH_TOKEN", ""),
        "ct0": os.getenv("X_CT0", ""),
        "twid": os.getenv("X_TWID", ""),
        "x_csrf_token": os.getenv("X_CSRF_TOKEN", ""),
    }


def load_control():
    if CONTROL_FILE_DISABLED:
        return {"active_account": "main", "accounts": {}}

    if not CONTROL_FILE.exists():
        return {"active_account": "main", "accounts": {}}

    try:
        return json.loads(CONTROL_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"active_account": "main", "accounts": {}}


def get_active_account_config():
    control = load_control()
    env_account = get_env_account_config()
    active_account_key = (
        env_account["account_key"]
        or control.get("active_account")
        or "main"
    )
    accounts = control.get("accounts") or {}
    active_account = accounts.get(active_account_key, {})

    account = {
        "account_key": active_account_key,
        "owner_username": active_account.get("owner_username", ""),
        "auth_token": active_account.get("auth_token", ""),
        "ct0": active_account.get("ct0", ""),
        "twid": active_account.get("twid", ""),
        "x_csrf_token": active_account.get("x-csrf-token") or active_account.get("x_csrf_token", ""),
    }

    for key in ["owner_username", "auth_token", "ct0", "twid", "x_csrf_token"]:
        if env_account[key]:
            account[key] = env_account[key]

    return account


def get_active_account_info():
    account = get_active_account_config()
    return {
        "account_key": account["account_key"],
        "owner_username": account["owner_username"] or account["account_key"],
    }


def has_runtime_credentials():
    account = get_active_account_config()
    return bool(account["auth_token"] and account["ct0"])


def build_cookies():
    cookies = DEFAULT_COOKIES.copy()
    account = get_active_account_config()

    if account["auth_token"]:
        cookies["auth_token"] = account["auth_token"]
    if account["ct0"]:
        cookies["ct0"] = account["ct0"]
    if account["twid"]:
        cookies["twid"] = account["twid"]

    for cookie_name, env_name in COOKIE_ENV_MAP.items():
        env_value = os.getenv(env_name)
        if env_value:
            cookies[cookie_name] = env_value
    return cookies


def build_headers(cookies):
    bearer = os.getenv("X_BEARER_TOKEN", DEFAULT_BEARER)
    account = get_active_account_config()
    csrf_token = os.getenv("X_CSRF_TOKEN") or account["x_csrf_token"] or cookies["ct0"]

    return {
        "authorization":                f"Bearer {bearer}",
        "x-csrf-token":                 csrf_token,
        "x-twitter-active-user":        "yes",
        "x-twitter-auth-type":          "OAuth2Session",
        "x-twitter-client-language":    "en",
        "content-type":                 "application/json",
        "accept":                       "*/*",
        "accept-language":              "en-US,en;q=0.9",
        "user-agent":                   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
        "referer":                      "https://x.com/i/bookmarks",
        "sec-ch-ua":                    '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        "sec-ch-ua-mobile":             "?0",
        "sec-ch-ua-platform":           '"Windows"',
        "sec-fetch-dest":               "empty",
        "sec-fetch-mode":               "cors",
        "sec-fetch-site":               "same-origin",
    }


def get_bookmarks(cursor=None):
    page_size = int(os.getenv("X_BOOKMARKS_PAGE_SIZE", "100"))
    variables = {"count": page_size, "includePromotedContent": True}
    if cursor:
        variables["cursor"] = cursor

    params = {
        "variables": json.dumps(variables, separators=(',', ':')),
        "features":  FEATURES,
    }

    query_id = os.getenv("X_BOOKMARKS_QUERY_ID", DEFAULT_QUERY_ID)
    cookies = build_cookies()
    headers = build_headers(cookies)
    url = f"https://x.com/i/api/graphql/{query_id}/Bookmarks?{urlencode(params)}"
    resp = requests.get(url, headers=headers, cookies=cookies, timeout=30)

    if resp.status_code == 403:
        raise RuntimeError("403 from X. Update the ct0 and auth_token cookies.")
    if resp.status_code == 404:
        raise RuntimeError("404 from X. Update the Bookmarks query ID from DevTools.")

    resp.raise_for_status()
    return resp.json()


def extract_entries(data):
    instructions = (
        data.get("data", {})
            .get("bookmark_timeline_v2", {})
            .get("timeline", {})
            .get("instructions", [])
    )

    entries = []
    for inst in instructions:
        if inst.get("type") == "TimelineAddEntries":
            entries.extend(inst.get("entries", []))
        elif inst.get("type") == "TimelineReplaceEntry":
            entry = inst.get("entry")
            if entry:
                entries.append(entry)

    return entries


def extract_bookmark(entry):
    tweet_result = (
        entry.get("content", {})
             .get("itemContent", {})
             .get("tweet_results", {})
             .get("result", {})
    )
    if tweet_result.get("__typename") == "TweetWithVisibilityResults":
        tweet_result = tweet_result.get("tweet", tweet_result)

    core = tweet_result.get("core", {}).get("user_results", {}).get("result", {})
    legacy = tweet_result.get("legacy", {})
    media_items = (
        legacy.get("extended_entities", {}).get("media")
        or legacy.get("entities", {}).get("media")
        or []
    )
    media_thumbnail = ""
    media_type = ""
    media_url = ""
    media_video_url = ""
    if media_items:
        primary_media = media_items[0]
        media_thumbnail = primary_media.get("media_url_https") or primary_media.get("media_url", "")
        media_type = primary_media.get("type", "")
        media_url = media_thumbnail

        if media_type == "image" and media_thumbnail:
            separator = "&" if "?" in media_thumbnail else "?"
            media_url = f"{media_thumbnail}{separator}name=orig"

        if media_type in {"video", "animated_gif"}:
            variants = primary_media.get("video_info", {}).get("variants", [])
            mp4_variants = [
                variant
                for variant in variants
                if variant.get("content_type") == "video/mp4" and variant.get("url")
            ]
            if mp4_variants:
                best_variant = max(mp4_variants, key=lambda variant: variant.get("bitrate", 0))
                media_video_url = best_variant.get("url", "")

    screen_name = (
        core.get("legacy", {}).get("screen_name")
        or core.get("core", {}).get("screen_name")
        or "unknown"
    )
    author_name = (
        core.get("legacy", {}).get("name")
        or core.get("core", {}).get("name")
        or screen_name
    )
    tweet_id = legacy.get("id_str") or tweet_result.get("rest_id", "")
    if not tweet_id:
        return None

    created_at = legacy.get("created_at", "")
    created_at_iso = ""
    created_at_unix = 0
    if created_at:
        try:
            created_dt = parsedate_to_datetime(created_at)
            created_at_iso = created_dt.isoformat()
            created_at_unix = int(created_dt.timestamp())
        except (TypeError, ValueError, OverflowError):
            created_at_iso = ""
            created_at_unix = 0

    text = legacy.get("full_text") or legacy.get("text") or ""
    for media_item in media_items:
        short_media_url = media_item.get("url")
        if short_media_url:
            text = text.replace(short_media_url, "").strip()

    return {
        "tweet_id": tweet_id,
        "author_name": author_name,
        "screen_name": screen_name,
        "text": text,
        "created_at": created_at,
        "created_at_iso": created_at_iso,
        "created_at_unix": created_at_unix,
        "media_thumbnail": media_thumbnail,
        "media_type": media_type,
        "media_count": len(media_items),
        "media_url": media_url,
        "media_video_url": media_video_url,
        "link": f"https://x.com/{screen_name}/status/{tweet_id}",
    }


def scrape_bookmarks(delay_seconds=0):
    bookmarks = []
    seen_tweet_ids = set()
    cursor = None
    pages_scanned = 0

    while True:
        data = get_bookmarks(cursor)
        entries = extract_entries(data)
        next_cursor = None
        pages_scanned += 1

        if not entries:
            break

        for entry in entries:
            eid = entry.get("entryId", "")

            if "cursor-bottom" in eid:
                val = entry.get("content", {}).get("value")
                if val:
                    next_cursor = val
                continue

            try:
                bookmark = extract_bookmark(entry)
                if bookmark and bookmark["tweet_id"] not in seen_tweet_ids:
                    seen_tweet_ids.add(bookmark["tweet_id"])
                    bookmarks.append(bookmark)
            except Exception:
                continue

        if not next_cursor or next_cursor == cursor:
            break

        cursor = next_cursor
        if delay_seconds:
            time.sleep(delay_seconds)

    unique_authors = len({bookmark["screen_name"] for bookmark in bookmarks})
    return {
        "bookmarks": bookmarks,
        "pages_scanned": pages_scanned,
        "unique_authors": unique_authors,
    }


def export_links_text(bookmarks):
    return "\n".join(bookmark["link"] for bookmark in bookmarks)


def export_links_csv(bookmarks):
    rows = ["index,screen_name,author_name,tweet_id,created_at,media_type,link"]
    for index, bookmark in enumerate(bookmarks, start=1):
        rows.append(
            f'{index},{bookmark["screen_name"]},{bookmark["author_name"]},{bookmark["tweet_id"]},{bookmark["created_at_iso"]},{bookmark["media_type"]},{bookmark["link"]}'
        )
    return "\n".join(rows)


if __name__ == "__main__":
    print("🔍 Fetching your bookmarks...\n")
    result = scrape_bookmarks()
    links = result["bookmarks"]

    if links:
        print("\n" + "═" * 50)
        print(f"✅ TOTAL BOOKMARKED TWEETS : {len(links)}")
        print("═" * 50 + "\n")
        for i, link in enumerate(links, 1):
            print(f'{i:>4}. {link["link"]}')
