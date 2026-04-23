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

2. Copy `control.example.json` to `control.json`.

3. Fill in your own X account values in `control.json`:
   - `auth_token`
   - `ct0`
   - `twid`
   - `x-csrf-token`

4. Run the app:

```bash
python app.py
```

5. Open `http://127.0.0.1:5000`

## Notes

- `control.json` is intentionally gitignored so your live cookies stay local.
- `bookmark_atlas.db` is also gitignored because it contains your personal bookmark data.
- X may change its internal GraphQL query ID or request format, which can break bookmark fetching until the scraper is updated.
