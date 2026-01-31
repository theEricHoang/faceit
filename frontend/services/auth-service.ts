import { apiClient } from '@/services/api-client';
import { clearAllTokens, setAccessToken, setRefreshToken } from '@/services/secure-storage';
import { useAuthStore } from '@/stores/auth-store';
import type {
    AuthTokens,
    InstructorSignupRequest,
    InstructorSignupResponse,
    LoginRequest,
    LoginResponse,
    StudentSignupRequest,
    StudentSignupResponse,
} from '@/types/auth';

/**
 * Log in a user with email and password
 * Returns the login response with tokens and user data
 */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>('/auth/login', credentials, {
    skipAuth: true,
  });

  // Store tokens
  await Promise.all([
    setAccessToken(response.access_token),
    setRefreshToken(response.refresh_token),
  ]);

  // Update auth state with user data
  useAuthStore.getState().setUser({
    user_id: response.user_id,
    email: response.email,
    first_name: response.first_name,
    last_name: response.last_name,
    type: response.type,
  });

  return response;
}

/**
 * Register a new student account
 * Returns the signup response with tokens and user data
 */
export async function registerStudent(
  data: StudentSignupRequest
): Promise<StudentSignupResponse> {
  const response = await apiClient.post<StudentSignupResponse>(
    '/auth/signup/student',
    data,
    { skipAuth: true }
  );

  // Store tokens
  await Promise.all([
    setAccessToken(response.access_token),
    setRefreshToken(response.refresh_token),
  ]);

  // Update auth state with user data
  useAuthStore.getState().setUser({
    user_id: response.user_id,
    email: response.email,
    first_name: response.first_name,
    last_name: response.last_name,
    type: response.type,
  });

  return response;
}

/**
 * Register a new instructor account
 * Returns the signup response with tokens and user data
 */
export async function registerInstructor(
  data: InstructorSignupRequest
): Promise<InstructorSignupResponse> {
  const response = await apiClient.post<InstructorSignupResponse>(
    '/auth/signup/instructor',
    data,
    { skipAuth: true }
  );

  // Store tokens
  await Promise.all([
    setAccessToken(response.access_token),
    setRefreshToken(response.refresh_token),
  ]);

  // Update auth state with user data
  useAuthStore.getState().setUser({
    user_id: response.user_id,
    email: response.email,
    first_name: response.first_name,
    last_name: response.last_name,
    type: response.type,
  });

  return response;
}

/**
 * Log out the current user
 * Clears tokens from secure storage and resets auth state
 */
export async function logout(): Promise<void> {
  try {
    // Optionally notify the server about logout
    // await apiClient.post('/auth/logout');
  } catch (error) {
    // Ignore errors when logging out on server
    console.warn('Server logout failed:', error);
  } finally {
    // Always clear local auth state
    await clearAllTokens();
    useAuthStore.setState({ user: null, isAuthenticated: false });
  }
}

/**
 * Manually refresh the access token
 * This is typically handled automatically by the API client,
 * but can be called manually if needed
 */
export async function refreshTokens(): Promise<AuthTokens> {
  return apiClient.post<AuthTokens>('/auth/refresh', {
    refresh_token: await import('@/services/secure-storage').then((m) =>
      m.getRefreshToken()
    ),
  });
}
