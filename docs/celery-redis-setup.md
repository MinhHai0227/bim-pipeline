# Celery + Redis Setup

This project uses Redis as the Celery broker/result backend for background IFC processing.

## Run With Docker Compose

This is the recommended setup once you want an API container and a worker container.

```powershell
docker compose up -d postgres redis api worker
```

The `worker` service is the Celery worker. It is the Celery equivalent of an `rq worker` process.

Run database migrations when needed:

```powershell
docker compose run --rm api alembic upgrade head
```

## Run Manually On Windows

Use this mode when you run the API from your local virtual environment instead of Docker.

Start Redis:

```powershell
docker compose up -d redis
```

Start API:

```powershell
venv\Scripts\python.exe -m uvicorn src.main:app --reload
```

Start Celery worker:

On Windows, use the `solo` pool:

```powershell
venv\Scripts\celery.exe -A src.core.celery_app.celery_app worker --loglevel=info --pool=solo
```

## Import Endpoint

```text
POST /api/ifc/import
```

The endpoint uploads the IFC to Cloudflare R2, creates an `ifc_files` record with `status="uploaded"`, and enqueues the Celery task:

```text
ifc.process_uploaded_file
```

The worker downloads the IFC from R2, parses it, detects assets, writes validation issues, and updates the file status to `processed` or `failed`.
