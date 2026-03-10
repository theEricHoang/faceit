import {
    getAccessToken,
    getRefreshToken,
    setAccessToken,
    setRefreshToken,
} from '@/services/secure-storage';
import { useAuthStore } from '@/stores/auth-store';
import type { AuthTokens } from '@/types/auth';

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL;

if (!API_BASE_URL) {
  console.warn(
    'EXPO_PUBLIC_API_URL is not defined. API calls will fail. ' +
      'Please add it to your .env file.'
  );
}

type RequestMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

interface RequestOptions {
  headers?: Record<string, string>;
  body?: unknown;
  skipAuth?: boolean;
}

interface ApiError extends Error {
  status: number;
  data?: unknown;
}

function createApiError(message: string, status: number, data?: unknown): ApiError {
  const error = new Error(message) as ApiError;
  error.status = status;
  error.data = data;
  return error;
}

// Flag to prevent multiple simultaneous refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<AuthTokens | null> | null = null;

/**
 * Attempt to refresh the access token using the refresh token
 */
async function refreshTokens(): Promise<AuthTokens | null> {
  const refreshToken = await getRefreshToken();

  if (!refreshToken) {
    return null;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      return null;
    }

    const tokens: AuthTokens = await response.json();

    // Store the new tokens
    await Promise.all([
      setAccessToken(tokens.access_token),
      setRefreshToken(tokens.refresh_token),
    ]);

    return tokens;
  } catch (error) {
    console.error('Failed to refresh tokens:', error);
    return null;
  }
}

/**
 * Handle token refresh with deduplication
 * Ensures only one refresh request is made at a time
 */
async function handleTokenRefresh(): Promise<AuthTokens | null> {
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  isRefreshing = true;
  refreshPromise = refreshTokens().finally(() => {
    isRefreshing = false;
    refreshPromise = null;
  });

  return refreshPromise;
}

/**
 * Make an authenticated request to the API
 */
async function request<T>(
  method: RequestMethod,
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { headers = {}, body, skipAuth = false } = options;

  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  // Add authorization header if not skipping auth
  if (!skipAuth) {
    const accessToken = await getAccessToken();
    if (accessToken) {
      requestHeaders['Authorization'] = `Bearer ${accessToken}`;
    }
  }

  const url = `${API_BASE_URL}${endpoint}`;

  const fetchOptions: RequestInit = {
    method,
    headers: requestHeaders,
  };

  if (body !== undefined) {
    fetchOptions.body = JSON.stringify(body);
  }

  let response = await fetch(url, fetchOptions);

  // Handle 401 Unauthorized - attempt token refresh
  if (response.status === 401 && !skipAuth) {
    const newTokens = await handleTokenRefresh();

    if (newTokens) {
      // Retry the original request with the new access token
      requestHeaders['Authorization'] = `Bearer ${newTokens.access_token}`;
      fetchOptions.headers = requestHeaders;
      response = await fetch(url, fetchOptions);
    } else {
      // Refresh failed - clear auth state and redirect to login
      await useAuthStore.getState().clearAuth();
      throw createApiError('Session expired. Please log in again.', 401);
    }
  }

  // Handle non-OK responses
  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      errorData = await response.text();
    }

    throw createApiError(
      `Request failed with status ${response.status}`,
      response.status,
      errorData
    );
  }

  // Handle empty responses (204 No Content)
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// API client methods
export const apiClient = {
  get: <T>(endpoint: string, options?: Omit<RequestOptions, 'body'>) =>
    request<T>('GET', endpoint, options),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>('POST', endpoint, { ...options, body }),

  put: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>('PUT', endpoint, { ...options, body }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    request<T>('PATCH', endpoint, { ...options, body }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    request<T>('DELETE', endpoint, options),
};
