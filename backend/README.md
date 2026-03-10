# FaceIT Backend

FastAPI + Supabase backend for FaceIT. The backend consists of two separate processes: the **API server** (handles HTTP requests) and the **enrollment worker** (processes face embedding jobs from SQS).

## Structure

- `app/` - Main application code
  - `main.py` - FastAPI entrypoint
  - `api/` - API route definitions
  - `core/` - Core configuration
  - `db/` - Supabase and AWS client integrations
  - `models/` - ORM and data models
  - `schemas/` - Pydantic schemas
  - `services/` - Business logic and services
  - `utils/` - Utility functions
  - `worker/` - Enrollment worker (SQS consumer)
- `tests/` - Unit and integration tests
- `requirements.txt` - Python dependencies
- `.gitignore` - Git ignore rules

## Getting Started

1. Install [pyenv](https://github.com/pyenv/pyenv?tab=readme-ov-file#b-set-up-your-shell-environment-for-pyenv) and [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv)
   ⚠️ NOTE!! do the optional step with pyenv-virtualenv that activates virtual environments automatically


2. Create a new Python virtual environment version 3.12.2:

   **On macOS/Linux/Windows Powershell:**
   ```bash
   pyenv install 3.12.2
   pyenv virtualenv 3.12.2 backend
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Setup environment variables by copying `.env.example` to `.env`

5. Run the API server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --reload
   ```

6. Run the enrollment worker (separate terminal):
   ```bash
   python -m app.worker.enrollment_worker
   ```

   By default the worker exits after 3 consecutive empty polls (designed for scheduled ECS tasks). For local development, set `WORKER_MAX_EMPTY_POLLS=0` in `.env` to keep it running indefinitely.

   > **Note:** The API server and worker are **separate processes**. `POST /jobs` inserts a DB row and enqueues an SQS message; the worker picks it up on its next poll cycle. You need both running for end-to-end job processing.

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/services/test_auth_service.py -v
```

Run with coverage report:
```bash
pytest tests/ --cov=app --cov-report=term-missing
```

Run worker smoke test (requires AWS credentials and a real SQS queue):
```bash
python tests/smoke_test_worker.py --user-id <existing-auth-user-uuid>
```
