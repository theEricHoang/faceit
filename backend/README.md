# FaceIT Backend

FastAPI + Supabase backend for FaceIT. The backend consists of two separate processes: the **API server** (handles HTTP requests) and **workers** (process face embedding jobs from SQS).

## Structure

- `app/` - Main application code
  - `main.py` - FastAPI entrypoint
  - `api/` - API route definitions
  - `core/` - Core configuration
  - `db/` - Supabase and AWS client integrations
  - `models/` - ORM and data models
  - `schemas/` - Pydantic schemas
  - `services/` - Business logic and services
  - `utils/` - Utility functions (including face embedding extraction)
  - `worker/` - Background workers (SQS consumers)
    - `enrollment_worker.py` - Processes ENROLLMENT jobs (single face)
    - `attendance_worker.py` - Processes ATTENDANCE jobs (multiple faces)
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

7. Run the attendance worker (separate terminal, for attendance processing):
   ```bash
   python -m app.worker.attendance_worker
   ```

   By default workers exit after 3 consecutive empty polls (designed for scheduled ECS tasks). For local development, set `WORKER_MAX_EMPTY_POLLS=0` in `.env` to keep them running indefinitely.

   > **Note:** The API server and workers are **separate processes**. `POST /jobs` inserts a DB row and enqueues an SQS message; the worker picks it up on its next poll cycle. You need all processes running for end-to-end job processing.

## Workers

### Enrollment Worker
Processes **ENROLLMENT** jobs for student face registration:
- Expects a single face in the uploaded photo
- Extracts a 512-dimensional embedding using InsightFace/ArcFace
- Stores the embedding in `face_embeddings` table

### Attendance Worker
Processes **ATTENDANCE** jobs for classroom attendance:
- Detects ALL faces in a classroom photo
- Extracts embeddings for each detected face
- Matches faces against enrolled student embeddings using **cosine similarity** (threshold: 0.6)
- Writes results to `attendance_results` table (student_id + confidence, or NULL for unknown)
- Updates job with summary (present_count, unknown_count)

**Cosine Similarity Threshold:**
- Uses **0.6** as the default threshold (standard for ArcFace embeddings)
- Faces with similarity ≥ 0.6 are considered matches
- Configurable in `RecognitionService` initialization

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

Run worker smoke tests (requires AWS credentials and real SQS queues):
```bash
# Enrollment worker smoke test
python tests/smoke_test_worker.py --user-id <existing-auth-user-uuid>

# Attendance worker smoke test
python tests/smoke_test_attendance_worker.py \
    --class-id <class-uuid> \
    --instructor-id <instructor-uuid> \
    [--embedding-mode v0|v1]
```
