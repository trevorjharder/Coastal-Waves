# Coastal Waves Inventory

This repository now includes a lightweight FastAPI backend with SQLite/PostgreSQL support and a static dashboard frontend.

## Backend

Located in `backend/`.

### Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start the API (default: `localhost:8000`):

```bash
uvicorn app.main:app --reload
```

The API will initialize its schema automatically in `data.db`. Set `DATABASE_URL` to point at PostgreSQL if desired.

Inventory can be bulk-loaded from an Excel sheet using `POST /import/inventory?dry_run=true|false`. The importer expects the `Inventory` worksheet with these columns (case-insensitive): `Foreign Key` (serial number), `Item Desc`, `Location`, `Stocked`, `Sold`, `Quantity`. Dry-run mode returns validation results without writing to the database.

### Key endpoints

- `POST /paintings` | `GET /paintings`
- `POST /variants` | `GET /variants`
- `POST /locations` | `GET /locations`
- `POST /inventory` | `GET /inventory`
- `POST /transactions` | `GET /transactions`
- Reports: `GET /reports/stock`, `GET /reports/sales`, `GET /reports/home`
- Import: `POST /import/inventory` (Excel upload; set `dry_run` query param)
- Health: `GET /health`

Serial numbers follow `PTG-<PAINTING>-<VARIANT>-<LOCATION>-<####>` and are validated server-side.

## Frontend

Located in `frontend/`. The dashboard is a simple static site consuming the API and is now served by the backend itself at `/app/`.

Features:

- Dashboard tabs for home vs. external locations
- Location cards showing on-hand, sold, and revenue
- Inline forms to add paintings and product variants

## Desktop app

A bundled desktop entry point lives at `desktop_app.py`. It starts the FastAPI backend in a background thread, serves the bundled dashboard from the backend at `http://127.0.0.1:8000/app/`, and renders that page inside a native window using [pywebview](https://pywebview.flowrl.com/). No separate browser compatibility is required.

### Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-desktop.txt
python desktop_app.py
```

This starts the API and opens the desktop window pointed at the backend-served dashboard.

### Build a Windows executable

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-desktop.txt
pip install pyinstaller
pyinstaller \
  --noconfirm \
  --name "CoastalWavesInventory" \
  --add-data "frontend/*;frontend" \
  --paths backend \
  desktop_app.py
```

The resulting `dist/CoastalWavesInventory/CoastalWavesInventory.exe` can be distributed and launched directly.

## Project layout

```
backend/
  app/
    database.py
    main.py
    models.py
    schemas.py
    serials.py
  requirements.txt
frontend/
  index.html
  app.js
  styles.css
```
