import os
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path(__file__).with_name("bookmark_atlas.db")
DB_PATH = Path(
    os.getenv(
        "BOOKMARK_ATLAS_DB_PATH",
        "/tmp/bookmark_atlas.db" if os.getenv("VERCEL") else str(DEFAULT_DB_PATH),
    )
)


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_column(connection, table_name, column_name, definition):
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )


def init_db():
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS bookmarks (
                tweet_id TEXT PRIMARY KEY,
                screen_name TEXT NOT NULL,
                author_name TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT '',
                created_at_iso TEXT NOT NULL DEFAULT '',
                created_at_unix INTEGER NOT NULL DEFAULT 0,
                media_thumbnail TEXT NOT NULL DEFAULT '',
                media_type TEXT NOT NULL DEFAULT '',
                media_count INTEGER NOT NULL DEFAULT 0,
                media_url TEXT NOT NULL DEFAULT '',
                media_video_url TEXT NOT NULL DEFAULT '',
                link TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                is_favorite INTEGER NOT NULL DEFAULT 0,
                is_current INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS bookmark_tags (
                tweet_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                PRIMARY KEY (tweet_id, tag),
                FOREIGN KEY (tweet_id) REFERENCES bookmarks(tweet_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS fetch_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fetched_at TEXT NOT NULL,
                bookmark_count INTEGER NOT NULL,
                pages_scanned INTEGER NOT NULL,
                unique_authors INTEGER NOT NULL,
                account_key TEXT NOT NULL DEFAULT ''
            );
            """
        )
        ensure_column(connection, "bookmarks", "media_url", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "bookmarks", "media_video_url", "TEXT NOT NULL DEFAULT ''")
        ensure_column(connection, "bookmarks", "is_favorite", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(connection, "fetch_runs", "account_key", "TEXT NOT NULL DEFAULT ''")


def sanitize_tags(raw_tags):
    tags = []
    seen = set()

    if isinstance(raw_tags, str):
        candidates = raw_tags.split(",")
    else:
        candidates = raw_tags or []

    for candidate in candidates:
        tag = str(candidate).strip().lower().lstrip("#")
        if not tag:
            continue
        if tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)

    return tags


def _get_tags_map(connection, tweet_ids=None):
    if tweet_ids is not None and not tweet_ids:
        return {}

    query = "SELECT tweet_id, tag FROM bookmark_tags"
    params = []
    if tweet_ids is not None:
        placeholders = ",".join("?" for _ in tweet_ids)
        query += f" WHERE tweet_id IN ({placeholders})"
        params.extend(tweet_ids)

    query += " ORDER BY tag ASC"
    rows = connection.execute(query, params).fetchall()

    tags_map = {}
    for row in rows:
        tags_map.setdefault(row["tweet_id"], []).append(row["tag"])
    return tags_map


def _row_to_bookmark(row, tags_map):
    return {
        "tweet_id": row["tweet_id"],
        "screen_name": row["screen_name"],
        "author_name": row["author_name"],
        "text": row["text"],
        "created_at": row["created_at"],
        "created_at_iso": row["created_at_iso"],
        "created_at_unix": row["created_at_unix"],
        "media_thumbnail": row["media_thumbnail"],
        "media_type": row["media_type"],
        "media_count": row["media_count"],
        "media_url": row["media_url"],
        "media_video_url": row["media_video_url"],
        "link": row["link"],
        "is_favorite": bool(row["is_favorite"]),
        "is_current": bool(row["is_current"]),
        "first_seen_at": row["first_seen_at"],
        "last_seen_at": row["last_seen_at"],
        "tags": tags_map.get(row["tweet_id"], []),
    }


def save_bookmarks(bookmarks, stats, fetched_at, account_key=""):
    tweet_ids = [bookmark["tweet_id"] for bookmark in bookmarks]

    with get_connection() as connection:
        connection.execute("UPDATE bookmarks SET is_current = 0")

        for bookmark in bookmarks:
            existing = connection.execute(
                "SELECT first_seen_at FROM bookmarks WHERE tweet_id = ?",
                [bookmark["tweet_id"]],
            ).fetchone()
            first_seen_at = existing["first_seen_at"] if existing else fetched_at

            connection.execute(
                """
                INSERT INTO bookmarks (
                    tweet_id,
                    screen_name,
                    author_name,
                    text,
                    created_at,
                    created_at_iso,
                    created_at_unix,
                    media_thumbnail,
                    media_type,
                    media_count,
                    media_url,
                    media_video_url,
                    link,
                    first_seen_at,
                    last_seen_at,
                    is_current
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(tweet_id) DO UPDATE SET
                    screen_name = excluded.screen_name,
                    author_name = excluded.author_name,
                    text = excluded.text,
                    created_at = excluded.created_at,
                    created_at_iso = excluded.created_at_iso,
                    created_at_unix = excluded.created_at_unix,
                    media_thumbnail = excluded.media_thumbnail,
                    media_type = excluded.media_type,
                    media_count = excluded.media_count,
                    media_url = excluded.media_url,
                    media_video_url = excluded.media_video_url,
                    link = excluded.link,
                    last_seen_at = excluded.last_seen_at,
                    is_current = excluded.is_current
                """,
                [
                    bookmark["tweet_id"],
                    bookmark["screen_name"],
                    bookmark["author_name"],
                    bookmark["text"],
                    bookmark["created_at"],
                    bookmark["created_at_iso"],
                    bookmark["created_at_unix"],
                    bookmark["media_thumbnail"],
                    bookmark["media_type"],
                    bookmark["media_count"],
                    bookmark.get("media_url", ""),
                    bookmark.get("media_video_url", ""),
                    bookmark["link"],
                    first_seen_at,
                    fetched_at,
                ],
            )

        connection.execute(
            "INSERT INTO fetch_runs (fetched_at, bookmark_count, pages_scanned, unique_authors, account_key) VALUES (?, ?, ?, ?, ?)",
            [
                fetched_at,
                len(bookmarks),
                stats["pages_scanned"],
                stats["unique_authors"],
                account_key,
            ],
        )

        if not tweet_ids:
            connection.execute("UPDATE bookmarks SET is_current = 0")


def get_bookmarks(scope="current", query="", tag="", media_type="", favorite_only=False):
    where = []
    params = []

    if scope == "current":
        where.append("bookmarks.is_current = 1")

    if favorite_only:
        where.append("bookmarks.is_favorite = 1")

    normalized_query = query.strip().lower()
    if normalized_query:
        like_value = f"%{normalized_query}%"
        where.append(
            "(" \
            "lower(bookmarks.screen_name) LIKE ? OR " \
            "lower(bookmarks.author_name) LIKE ? OR " \
            "lower(bookmarks.text) LIKE ? OR " \
            "lower(bookmarks.link) LIKE ? OR " \
            "lower(bookmarks.tweet_id) LIKE ?" \
            ")"
        )
        params.extend([like_value] * 5)

    normalized_tag = tag.strip().lower()
    if normalized_tag:
        where.append(
            "EXISTS (SELECT 1 FROM bookmark_tags WHERE bookmark_tags.tweet_id = bookmarks.tweet_id AND lower(bookmark_tags.tag) LIKE ?)"
        )
        params.append(f"%{normalized_tag}%")

    normalized_media_type = media_type.strip().lower()
    if normalized_media_type == "none":
        where.append("bookmarks.media_type = ''")
    elif normalized_media_type:
        where.append("lower(bookmarks.media_type) = ?")
        params.append(normalized_media_type)

    query_text = "SELECT * FROM bookmarks"
    if where:
        query_text += " WHERE " + " AND ".join(where)
    query_text += " ORDER BY bookmarks.created_at_unix DESC, bookmarks.last_seen_at DESC"

    with get_connection() as connection:
        rows = connection.execute(query_text, params).fetchall()
        tags_map = _get_tags_map(connection, [row["tweet_id"] for row in rows])
        return [_row_to_bookmark(row, tags_map) for row in rows]


def get_bookmark(tweet_id):
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM bookmarks WHERE tweet_id = ?", [tweet_id]).fetchone()
        if row is None:
            return None
        tags_map = _get_tags_map(connection, [tweet_id])
        return _row_to_bookmark(row, tags_map)


def update_bookmark_tags(tweet_id, raw_tags):
    tags = sanitize_tags(raw_tags)

    with get_connection() as connection:
        exists = connection.execute("SELECT 1 FROM bookmarks WHERE tweet_id = ?", [tweet_id]).fetchone()
        if exists is None:
            return None

        connection.execute("DELETE FROM bookmark_tags WHERE tweet_id = ?", [tweet_id])
        connection.executemany(
            "INSERT INTO bookmark_tags (tweet_id, tag) VALUES (?, ?)",
            [[tweet_id, tag] for tag in tags],
        )

    return get_bookmark(tweet_id)


def set_bookmark_favorite(tweet_id, is_favorite):
    with get_connection() as connection:
        exists = connection.execute("SELECT 1 FROM bookmarks WHERE tweet_id = ?", [tweet_id]).fetchone()
        if exists is None:
            return None

        connection.execute(
            "UPDATE bookmarks SET is_favorite = ? WHERE tweet_id = ?",
            [1 if is_favorite else 0, tweet_id],
        )

    return get_bookmark(tweet_id)


def get_dashboard_stats():
    with get_connection() as connection:
        latest_run = connection.execute(
            "SELECT fetched_at, bookmark_count, pages_scanned, unique_authors, account_key FROM fetch_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        current_total = connection.execute(
            "SELECT COUNT(*) AS count FROM bookmarks WHERE is_current = 1"
        ).fetchone()["count"]
        library_total = connection.execute(
            "SELECT COUNT(*) AS count FROM bookmarks"
        ).fetchone()["count"]
        tagged_total = connection.execute(
            "SELECT COUNT(DISTINCT tweet_id) AS count FROM bookmark_tags"
        ).fetchone()["count"]
        favorite_total = connection.execute(
            "SELECT COUNT(*) AS count FROM bookmarks WHERE is_favorite = 1"
        ).fetchone()["count"]

    return {
        "current_total": current_total,
        "library_total": library_total,
        "tagged_total": tagged_total,
        "favorite_total": favorite_total,
        "fetched_at": latest_run["fetched_at"] if latest_run else None,
        "pages_scanned": latest_run["pages_scanned"] if latest_run else 0,
        "unique_authors": latest_run["unique_authors"] if latest_run else 0,
        "fetched_account_key": latest_run["account_key"] if latest_run else "",
    }


def has_cache():
    with get_connection() as connection:
        row = connection.execute("SELECT 1 FROM bookmarks LIMIT 1").fetchone()
        return row is not None


def get_latest_fetch_account_key():
    with get_connection() as connection:
        latest_run = connection.execute(
            "SELECT account_key FROM fetch_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if latest_run is None:
            return ""
        return latest_run["account_key"] or ""
