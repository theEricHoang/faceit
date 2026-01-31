import { apiClient } from '@/services/api-client';
import { clearAllTokens, setAccessToken, setRefreshToken } from '@/services/secure-storage';
import { useAuthStore } from '@/stores/auth-store';
import type { AuthTokens } from '@/types/auth';

interface LoginRequest {
  email: string;
  password: string;
}

/**
 * Log in a user with email and password
 * Returns the auth tokens on success
 */
export async function login(credentials: LoginRequest): Promise<AuthTokens> {
  const tokens = await apiClient.post<AuthTokens>('/auth/login', credentials, {
    skipAuth: true,
  });

  // Store tokens and update auth state
  await Promise.all([
    setAccessToken(tokens.access_token),
    setRefreshToken(tokens.refresh_token),
  ]);

  useAuthStore.getState().setUser;
  useAuthStore.setState({ isAuthenticated: true });

  return tokens;
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
