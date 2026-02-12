# AGENTS.md - Coding Agent Guidelines for FaceIT

## Project Overview
FaceIT is a facial recognition-based attendance system with a FastAPI/Supabase backend and Expo/React Native mobile frontend (iOS, Android, web). The backend handles instructor/student authentication, class management, and attendance tracking. The frontend uses file-based routing with React 19 and Expo SDK 54.

## Build/Lint/Test Commands

### Frontend (from `frontend/` directory)
```bash
npm install                 # Install dependencies
npx expo start             # Start dev server (press i/a/w for platform)
npm run ios                # Start iOS simulator
npm run android            # Start Android emulator
npm run web                # Start in web browser
npm run lint               # Run ESLint
```

### Backend (from `backend/` directory)
```bash
# Setup
pyenv install 3.12.2
pyenv virtualenv 3.12.2 backend
pip install -r requirements.txt

# Development
uvicorn app.main:app --host 0.0.0.0 --reload    # Start dev server

# Testing
pytest tests/ -v                                 # Run all tests
pytest tests/services/test_auth_service.py -v   # Run single test file
pytest tests/api/test_auth.py::test_signup -v   # Run single test
pytest tests/ --cov=app --cov-report=term-missing  # With coverage
```

### Environment Setup
- **Backend**: Copy `backend/.env.example` to `backend/.env` (requires `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`)
- **Frontend**: Copy `frontend/.env.example` to `frontend/.env` (requires `EXPO_PUBLIC_API_URL`)

## Architecture & Patterns

### Backend Layer Structure
```
Routes (api/routes/) → Services (services/) → Supabase Client (db/supabase.py)
     ↑                       ↑
  Schemas                 Models
(schemas/)              (models/)
```

- **Routes**: HTTP endpoint handlers - validate input via Pydantic schemas, delegate to services, map service exceptions to HTTP errors
- **Services**: Business logic layer - orchestrate Supabase operations, handle rollbacks, raise domain-specific exceptions
- **Models**: Pydantic models representing database tables (e.g., `ProfileType` enum mirrors DB constraints)
- **Schemas**: Request/response DTOs with validation rules

### Frontend Architecture
- **File-based routing**: `app/` directory with expo-router
- **Route groups**: Use `(parentheses)` - they organize routes without affecting URL paths
- **State management**: Zustand store with expo-secure-store persistence
- **API layer**: `services/api-client.ts` handles auth headers and token refresh automatically
- **Theming**: Use `ThemedText`/`ThemedView` components for auto dark/light mode

## Code Style Guidelines

### Backend (Python)

#### File & Naming Conventions
- **Files**: `snake_case.py` (e.g., `auth_service.py`, `user_profile_service.py`)
- **Classes**: `PascalCase` (e.g., `AuthService`, `EnrollmentService`)
- **Functions/methods**: `snake_case` (e.g., `signup_instructor`, `get_current_user`)
- **Route files**: Match resource name (`auth.py`, `users.py`, `classes.py`)
- **Service files**: `{resource}_service.py` pattern
- **Schema/model files**: Match database table (`user.py`, `course.py`, `attendance.py`)

#### Service Pattern (CRITICAL)
```python
class MyService:
    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()  # Enables test injection

    async def my_operation(self, request: MyRequest) -> MyResponse:
        # Multi-step operations MUST implement rollback on failure
        # See signup_instructor() in app/services/auth_service.py for pattern
```

#### Exception Handling
Each service defines its own exception hierarchy:
```python
class AuthServiceError(Exception): pass
class SignupError(AuthServiceError): pass
class LoginError(AuthServiceError): pass
```

Routes catch service exceptions and map to HTTP status codes:
```python
@router.post("/endpoint", response_model=ResponseSchema, status_code=status.HTTP_201_CREATED)
async def handler(request: RequestSchema) -> ResponseSchema:
    service = MyService()
    try:
        return await service.operation(request)
    except ServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
```

#### Supabase Integration
- Single cached client via `get_supabase_client()` in `app/db/supabase.py`
- Uses **service key** (bypasses RLS) for all server-side operations
- Auth operations: `client.auth.sign_up()`, `client.auth.sign_in_with_password()`
- Table operations: `client.table("table_name").insert().execute()`

#### Testing Patterns
- Fixtures in `tests/conftest.py` provide mock Supabase client and sample data
- Services accept optional `client` parameter for dependency injection during tests
- Use `MockAuthResponse`, `MockTableResponse` classes for Supabase response mocking

```python
@pytest.mark.asyncio
async def test_operation(self, mock_supabase_client: MagicMock):
    service = MyService(client=mock_supabase_client)  # Inject mock
    result = await service.operation(request)
    mock_supabase_client.table.assert_called_with("expected_table")
```

### Frontend (TypeScript/React Native)

#### File & Naming Conventions
- **Files**: `kebab-case.tsx` (e.g., `themed-text.tsx`, `haptic-tab.tsx`)
- **Components**: `PascalCase` exports (e.g., `ThemedText`, `HapticTab`)
- **Hooks**: `use-kebab-case.ts` files with `useCamelCase` exports
- **Variables**: `camelCase` (e.g., `isAuthenticated`, `accessToken`)

#### Import Conventions
Use the `@/` path alias for absolute imports:
```tsx
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { apiClient } from '@/services/api-client';
```

#### Theming Pattern (CRITICAL)
Always use themed components instead of raw React Native primitives:
```tsx
// ✅ Correct - auto dark/light mode
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';

// ❌ Avoid - no theme support
import { Text, View } from 'react-native';
```

Access theme colors via hooks:
```tsx
const color = useThemeColor({ light: '#fff', dark: '#000' }, 'background');
```

#### API Client Pattern (CRITICAL)
Always use `apiClient` for API calls — it handles auth headers and token refresh automatically:
```tsx
import { apiClient } from '@/services/api-client';

// Authenticated requests
const data = await apiClient.get<ResponseType>('/endpoint');
const result = await apiClient.post<ResponseType>('/endpoint', { body: 'data' });

// Skip auth for public endpoints
await apiClient.post('/auth/login', credentials, { skipAuth: true });
```

**Features:**
- Auto-injects `Authorization: Bearer` header from stored access token
- On 401 response: attempts token refresh via `POST /auth/refresh`, retries original request
- On refresh failure: clears auth state (triggers redirect to login)

#### Auth Store Pattern
Global auth state using Zustand with expo-secure-store persistence:
```tsx
import { useAuthStore } from '@/stores/auth-store';

// Reading state (use selectors for performance)
const user = useAuthStore((state) => state.user);
const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

// Actions
useAuthStore.getState().setUser(user);
useAuthStore.getState().setTokens(tokens);
await useAuthStore.getState().clearAuth();
```

#### Protected Routes
Wrap protected layouts with `ProtectedRoute`:
```tsx
import { ProtectedRoute } from '@/components/protected-route';

export default function ProtectedLayout() {
  return (
    <ProtectedRoute>
      <Stack />
    </ProtectedRoute>
  );
}
```

#### TypeScript Configuration
- Strict mode enabled
- Path alias: `@/*` maps to root directory
- Experimental features: `typedRoutes`, `reactCompiler`

## Domain Concepts

### User Types
- **ProfileType**: Enum (`student`/`instructor`) - stored in `profiles.type` column
- **Multi-table user creation**: Auth user → profiles → instructors/students (with rollback)
- User types share `profiles` table, with role-specific data in `instructors` or `students`

### Authentication Flow
1. Frontend calls `POST /auth/login` with credentials
2. Backend validates with Supabase Auth, returns tokens
3. Frontend stores tokens in expo-secure-store
4. API client auto-injects Bearer token in subsequent requests
5. On 401, API client refreshes token and retries

## Key Dependencies

### Frontend
- **expo-router**: File-based navigation
- **zustand**: Global state management
- **expo-secure-store**: Secure token storage (iOS Keychain, Android Keystore)
- **expo-image**: Optimized image component (prefer over `Image` from react-native)

### Backend
- **FastAPI**: Web framework
- **Supabase**: Auth and database
- **Pydantic**: Schema validation and settings management
- **pytest**: Testing framework
