# FaceIT Backend - AI Coding Instructions

## Project Overview
FaceIT is a facial recognition-based attendance system backend built with **FastAPI** and **Supabase**. The system handles instructor/student authentication, class management, and attendance tracking via face recognition.

## Architecture

### Layer Structure
```
Routes (api/routes/) → Services (services/) → Supabase Client (db/supabase.py)
     ↑                       ↑
  Schemas                  Models
(schemas/)              (models/)
```

- **Routes**: HTTP endpoint handlers - validate input via Pydantic schemas, delegate to services, map service exceptions to HTTP errors
- **Services**: Business logic layer - orchestrate Supabase operations, handle rollbacks, raise domain-specific exceptions
- **Models**: Pydantic models representing database tables (e.g., `ProfileType` enum mirrors DB constraints)
- **Schemas**: Request/response DTOs with validation rules

### Supabase Integration
- Single cached client via `get_supabase_client()` in [app/db/supabase.py](app/db/supabase.py)
- Uses **service key** (bypasses RLS) for all server-side operations
- Auth operations: `client.auth.sign_up()`, `client.auth.sign_in_with_password()`
- Table operations: `client.table("table_name").insert().execute()`

## Key Patterns

### Service Pattern (follow [app/services/auth_service.py](app/services/auth_service.py))
```python
class MyService:
    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()  # Enables test injection

    async def my_operation(self, request: MyRequest) -> MyResponse:
        # Multi-step operations should implement rollback on failure
        # See signup_instructor() for rollback pattern
```

### Exception Hierarchy
Each service defines its own exception classes inheriting from a base:
```python
class AuthServiceError(Exception): pass
class SignupError(AuthServiceError): pass
class LoginError(AuthServiceError): pass
```
Routes catch these and map to appropriate HTTP status codes.

### Route Handler Pattern
```python
@router.post("/endpoint", response_model=ResponseSchema, status_code=status.HTTP_201_CREATED)
async def handler(request: RequestSchema) -> ResponseSchema:
    service = MyService()
    try:
        return await service.operation(request)
    except ServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
```

## Testing

### Running Tests
```bash
pytest tests/ -v                              # All tests
pytest tests/services/test_auth_service.py -v # Specific file
pytest tests/ --cov=app --cov-report=term-missing  # With coverage
```

### Test Structure
- Fixtures in [tests/conftest.py](tests/conftest.py) provide mock Supabase client and sample data
- Services accept optional `client` parameter for dependency injection during tests
- Use `MockAuthResponse`, `MockTableResponse` classes for Supabase response mocking

### Mocking Pattern
```python
@pytest.mark.asyncio
async def test_operation(self, mock_supabase_client: MagicMock):
    service = MyService(client=mock_supabase_client)  # Inject mock
    result = await service.operation(request)
    mock_supabase_client.table.assert_called_with("expected_table")
```

## Development

### Environment Setup
- Python 3.12.2 via pyenv with virtualenv named `backend`
- Copy `.env.example` to `.env` with `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`
- Run: `uvicorn app.main:app --reload`

### Configuration
Settings loaded via pydantic-settings in [app/core/config.py](app/core/config.py) - add new env vars there.

## Domain Concepts
- **ProfileType**: Enum (`student`/`instructor`) - stored in `profiles.type` column
- **Multi-table user creation**: Auth user → profiles → instructors/students (with rollback)
- User types share `profiles` table, with role-specific data in `instructors` or `students`

## File Naming Conventions
- Route files match resource name: `auth.py`, `users.py`, `classes.py`
- Schema/model files match database table: `user.py` (profiles), `class.py`, `attendance.py`
- Service files: `{resource}_service.py`
