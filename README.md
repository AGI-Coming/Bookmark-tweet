# Bookmark Atlas

A small Flask app for viewing, searching, tagging, and exporting your saved X/Twitter bookmarks.

## What it does

- Fetches bookmarks from X using your logged-in account cookies
- Stores bookmarks in a local SQLite database
- Lets you search the current cache or the full local library
- Supports favorites, tags, CSV export, and TXT export
- Shows tweet media previews and embedded tweets in the browser

## Setup

1. Create a virtual environment and install dependencies:

```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env`.

3. Fill in your own X account values in `.env`:
   - `X_AUTH_TOKEN`
   - `X_CT0`
   - `X_TWID`
   - `X_CSRF_TOKEN`
   - `X_OWNER_USERNAME` (optional)

4. Run the app:

```bash
python app.py
```

5. Open `http://127.0.0.1:5000`

## Notes

- `.env` is now the preferred local configuration file and is gitignored.
- `control.json` is intentionally gitignored so your live cookies stay local.
- `control.json` is still supported as a fallback if you prefer it.
- You can point to a different control file with `BOOKMARK_ATLAS_CONTROL_FILE`.
- You can disable control-file loading entirely with `BOOKMARK_ATLAS_DISABLE_CONTROL_FILE=1`.
- `bookmark_atlas.db` is also gitignored because it contains your personal bookmark data.
- X may change its internal GraphQL query ID or request format, which can break bookmark fetching until the scraper is updated.
- On Vercel, the app uses `/tmp/bookmark_atlas.db`, which is temporary storage and does not persist across restarts.

## Vercel

Set these environment variables in your Vercel project before trying to refresh bookmarks online:

- `X_AUTH_TOKEN`
- `X_CT0`
- `X_TWID`
- `X_CSRF_TOKEN`
- `X_OWNER_USERNAME` (optional, for display only)
