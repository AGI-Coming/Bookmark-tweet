from datetime import datetime, timezone
import threading

import requests
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from getTweetLink import (
    export_links_csv,
    export_links_text,
    get_active_account_info,
    has_runtime_credentials,
    scrape_bookmarks,
)
from storage import (
    get_bookmark,
    get_bookmarks,
    get_dashboard_stats,
    get_latest_fetch_account_key,
    has_cache,
    init_db,
    save_bookmarks,
    set_bookmark_favorite,
    update_bookmark_tags,
)


app = Flask(__name__)
init_db()

refresh_lock = threading.Lock()
refresh_state = {
    "running": False,
    "last_error": "",
    "last_started_at": None,
    "last_finished_at": None,
    "last_account_key": "",
}


MISSING_CREDENTIALS_MESSAGE = (
    "No X credentials are configured for this deployment yet. "
    "Add X_AUTH_TOKEN, X_CT0, X_TWID, X_CSRF_TOKEN, and optionally X_OWNER_USERNAME "
    "in Vercel Project Settings, then redeploy."
)


def serialize_payload(bookmarks, source, view, message=""):
    stats = get_dashboard_stats()
    return {
        "ok": True,
        "source": source,
        "view": view,
        "account": get_active_account_info(),
        "message": message,
        "bookmarks": bookmarks,
        "stats": {
            **stats,
            "loaded_total": len(bookmarks),
        },
    }


def refresh_cache():
    result = scrape_bookmarks()
    fetched_at = datetime.now(timezone.utc).isoformat()
    save_bookmarks(
        result["bookmarks"],
        result,
        fetched_at,
        account_key=get_active_account_info()["account_key"],
    )
    return get_bookmarks(scope="current")


def get_refresh_state():
    with refresh_lock:
        return dict(refresh_state)


def run_refresh_job(account_key):
    error_message = ""

    try:
        refresh_cache()
    except Exception as exc:
        error_message = str(exc)

    with refresh_lock:
        refresh_state["running"] = False
        refresh_state["last_error"] = error_message
        refresh_state["last_finished_at"] = datetime.now(timezone.utc).isoformat()
        refresh_state["last_account_key"] = account_key


def start_refresh_job():
    account_key = get_active_account_info()["account_key"]

    with refresh_lock:
        if refresh_state["running"]:
            return False

        refresh_state["running"] = True
        refresh_state["last_error"] = ""
        refresh_state["last_started_at"] = datetime.now(timezone.utc).isoformat()
        refresh_state["last_finished_at"] = None
        refresh_state["last_account_key"] = account_key

    thread = threading.Thread(target=run_refresh_job, args=(account_key,), daemon=True)
    thread.start()
    return True


@app.get("/")
def index():
    return render_template("index.html", page_mode="dashboard")


@app.get("/all-bookmarks")
def all_bookmarks_page():
    return render_template("index.html", page_mode="all-bookmarks")


@app.get("/favorites")
def favorites_page():
    return render_template("index.html", page_mode="favorites")


@app.get("/api/bookmarks")
def bookmarks_api():
    try:
        active_account = get_active_account_info()
        latest_fetch_account_key = get_latest_fetch_account_key()
        cache_exists = has_cache()
        can_refresh = has_runtime_credentials()
        needs_refresh = (not cache_exists) or latest_fetch_account_key != active_account["account_key"]

        if needs_refresh and can_refresh:
            bookmarks = refresh_cache()
            return jsonify(serialize_payload(bookmarks, source="live", view="current"))

        if not cache_exists:
            return jsonify(
                serialize_payload(
                    [],
                    source="empty",
                    view="current",
                    message=MISSING_CREDENTIALS_MESSAGE,
                )
            )

        bookmarks = get_bookmarks(scope="current")
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    message = ""
    if not has_runtime_credentials():
        message = (
            "Showing cached data only. Configure X credentials in Vercel if you want refreshes to work online."
        )

    return jsonify(serialize_payload(bookmarks, source="cache", view="current", message=message))


@app.post("/api/bookmarks/refresh")
def refresh_bookmarks_api():
    if not has_runtime_credentials():
        return jsonify({"ok": False, "error": MISSING_CREDENTIALS_MESSAGE}), 400

    started = start_refresh_job()
    state = get_refresh_state()
    return jsonify(
        {
            "ok": True,
            "started": started,
            "running": state["running"],
            "account": get_active_account_info(),
        }
    )


@app.get("/api/bookmarks/refresh-status")
def refresh_bookmarks_status_api():
    state = get_refresh_state()
    return jsonify(
        {
            "ok": True,
            "running": state["running"],
            "last_error": state["last_error"],
            "last_started_at": state["last_started_at"],
            "last_finished_at": state["last_finished_at"],
            "last_account_key": state["last_account_key"],
            "stats": get_dashboard_stats(),
        }
    )


@app.get("/api/bookmarks/<tweet_id>/video")
def bookmark_video_proxy_api(tweet_id):
    bookmark = get_bookmark(tweet_id)
    if bookmark is None or not bookmark.get("media_video_url"):
        return jsonify({"ok": False, "error": "Video not found."}), 404

    upstream_headers = {}
    range_header = request.headers.get("Range")
    if range_header:
        upstream_headers["Range"] = range_header

    upstream = requests.get(
        bookmark["media_video_url"],
        headers=upstream_headers,
        stream=True,
        timeout=60,
    )

    response_headers = {}
    for header_name in [
        "Content-Type",
        "Content-Length",
        "Content-Range",
        "Accept-Ranges",
        "Cache-Control",
        "ETag",
        "Last-Modified",
    ]:
        header_value = upstream.headers.get(header_name)
        if header_value:
            response_headers[header_name] = header_value

    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=1024 * 64):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return Response(
        stream_with_context(generate()),
        status=upstream.status_code,
        headers=response_headers,
        direct_passthrough=True,
    )


@app.get("/api/library")
def library_api():
    query = request.args.get("q", "")
    tag = request.args.get("tag", "")
    media_type = request.args.get("media_type", "")
    scope = request.args.get("scope", "all")

    if scope not in {"all", "current"}:
        scope = "all"

    try:
        bookmarks = get_bookmarks(scope=scope, query=query, tag=tag, media_type=media_type)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    payload = serialize_payload(bookmarks, source="cache", view="library")
    payload["filters"] = {
        "q": query,
        "tag": tag,
        "media_type": media_type,
        "scope": scope,
    }
    return jsonify(payload)


@app.get("/api/favorites")
def favorites_api():
    try:
        bookmarks = get_bookmarks(scope="all", favorite_only=True)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify(serialize_payload(bookmarks, source="cache", view="favorites"))


@app.post("/api/bookmarks/<tweet_id>/tags")
def update_tags_api(tweet_id):
    payload = request.get_json(silent=True) or {}

    try:
        bookmark = update_bookmark_tags(tweet_id, payload.get("tags", []))
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    if bookmark is None:
        return jsonify({"ok": False, "error": "Bookmark not found."}), 404

    return jsonify({"ok": True, "bookmark": bookmark})


@app.post("/api/bookmarks/<tweet_id>/favorite")
def favorite_bookmark_api(tweet_id):
    payload = request.get_json(silent=True) or {}

    try:
        bookmark = set_bookmark_favorite(tweet_id, bool(payload.get("is_favorite")))
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    if bookmark is None:
        return jsonify({"ok": False, "error": "Bookmark not found."}), 404

    return jsonify({"ok": True, "bookmark": bookmark})


@app.get("/api/export.txt")
def export_txt_api():
    if not has_cache():
        if not has_runtime_credentials():
            return jsonify({"ok": False, "error": MISSING_CREDENTIALS_MESSAGE}), 400
        refresh_cache()

    bookmarks = get_bookmarks(scope="current")
    text_payload = export_links_text(bookmarks)
    return Response(
        text_payload,
        mimetype="text/plain",
        headers={"Content-Disposition": 'attachment; filename="bookmarks.txt"'},
    )


@app.get("/api/export.csv")
def export_csv_api():
    if not has_cache():
        if not has_runtime_credentials():
            return jsonify({"ok": False, "error": MISSING_CREDENTIALS_MESSAGE}), 400
        refresh_cache()

    bookmarks = get_bookmarks(scope="current")
    csv_payload = export_links_csv(bookmarks)
    return Response(
        csv_payload,
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="bookmarks.csv"'},
    )


if __name__ == "__main__":
    app.run(debug=True)
