# Web Downloader Portal
[ This project is generated entirely from Codex AI ]

Open-source web solution for downloading files from URL with user isolation and file sharing.

## Features

- User registration and login.
- Per-user private download folders (`storage/users/<user_id>`).
- Global shared folder (`storage/global`) for files visible to all authenticated users.
- File explorer style listing for private/global locations.
- Actions: download, rename, move to global, create temporary share URL.
- URL input field to trigger your existing `downloader.py` script from the UI.

## Quick start (local Python)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

## Docker Compose deployment

1. (Optional) Create a `.env` file:

```env
SECRET_KEY=replace-with-a-long-random-secret
SHARE_TTL_SECONDS=3600
```

2. Build and start:

```bash
docker compose up -d --build
```

3. View logs:

```bash
docker compose logs -f web
```

4. Stop service:

```bash
docker compose down
```

The app is exposed on `http://localhost:5000`.

### Persistent data in Docker

- `downloader_data` volume: stores SQLite DB at `/app/data/app.db`
- `downloader_storage` volume: stores user/global downloaded files at `/app/storage`

## Configuration

Environment variables:

- `SECRET_KEY`: Flask secret key.
- `DATABASE_URL`: SQLAlchemy database URL (defaults to local SQLite `app.db`).
- `SHARE_TTL_SECONDS`: temporary link lifetime in seconds (default `3600`).

## Notes

- Temporary URLs are implemented with signed tokens and TTL validation.
- Deploy easily with any WSGI host (gunicorn, uwsgi) and reverse proxy.
