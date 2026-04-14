# LaTeX Compile Service

A self-hosted LaTeX-as-a-Service REST API for compiling single `.tex` files and full LaTeX projects. Built with FastAPI, Celery, Redis, and a full TeX Live container.

## Key features

- `POST /api/v1/compile` for single-file or ZIP project compilation
- `GET /api/v1/health` and `GET /api/v1/metrics`
- Background compilation with Celery + Redis
- API key authentication via `X-API-Key`
- Strict sandbox defaults: no shell escape by default
- Prometheus-compatible metrics endpoint
- Production-ready Docker + docker-compose setup

## Quickstart

1. Copy `.env.example` to `.env` and set a strong `API_KEY`.
2. Start the stack:

```bash
docker compose up --build
```

The Compose stack includes healthchecks for the API and Redis services. Use `docker compose ps` to confirm service health and `docker compose logs -f api` to inspect startup output.

3. Call the compile endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/compile" \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@document.tex" \
  -F "engine=pdflatex"
```

The service expects `X-API-Key` in request headers and will reject unauthenticated requests.

## API

### `POST /api/v1/compile`

Accepts `multipart/form-data`:

- `file` — `.tex` file or ZIP archive containing the project
- `main_tex` — required when sending a ZIP archive
- `engine` — `pdflatex`, `xelatex`, or `lualatex` (default: `pdflatex`)
- `shell_escape` — `true` or `false` (default: `false`)
- `timeout` — compilation timeout in seconds

Returns JSON:

- `status` — `success` or `failure`
- `pdf` — base64-encoded PDF content
- `log` — full LaTeX compilation log
- `errors` — array of parsed errors

### `POST /api/v1/compile/async`

Accepts the same `multipart/form-data` payload as `/api/v1/compile`, but returns a Celery task identifier immediately for background processing.

Returns JSON:

- `task_id` — the Celery task identifier
- `state` — current task state, such as `PENDING` or `RECEIVED`

Example:

```bash
curl -X POST "http://localhost:8000/api/v1/compile/async" \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@document.tex" \
  -F "engine=pdflatex"
```

### `GET /api/v1/compile/{task_id}`

Query a submitted compile job:

- `task_id` — the Celery task identifier
- `state` — the current task state
- `status` — compilation status once complete
- `pdf` — base64-encoded PDF content when available
- `log` — task compilation log
- `errors` — parsed LaTeX errors
- `detail` — failure detail if the task failed

Example:

```bash
curl "http://localhost:8000/api/v1/compile/<task_id>" \
  -H "X-API-Key: YOUR_API_KEY"
```

### `GET /api/v1/health`

Returns basic liveness information.

### `GET /api/v1/metrics`

Returns Prometheus-style metrics.

## Security notes

- `shell_escape` is disabled by default for safety.
- The service runs inside a container and should be deployed behind a gateway or API proxy.
- Use a secure `API_KEY` and do not commit `.env` to Git.
- File uploads are validated for size and allowed extensions.

## Development

Install dependencies locally:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Install development dependencies for tests:

```bash
pip install -e .[dev]
```

Run the API locally:

```bash
uvicorn latex_compile_service.main:app --reload --host 0.0.0.0 --port 8000
```

Run tests:

```bash
pytest
```
