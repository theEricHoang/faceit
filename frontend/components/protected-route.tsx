import { useRouter, useSegments } from 'expo-router';
import { useEffect } from 'react';

import { useAuthStore } from '@/stores/auth-store';

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** The route to redirect to when not authenticated. Defaults to '/login' */
  loginRoute?: string;
}

/**
 * A component that protects routes by checking authentication status.
 * Redirects to the login route if the user is not authenticated.
 *
 * Usage:
 * ```tsx
 * // In a layout file (e.g., app/(protected)/_layout.tsx)
 * import { ProtectedRoute } from '@/components/protected-route';
 *
 * export default function ProtectedLayout() {
 *   return (
 *     <ProtectedRoute>
 *       <Stack />
 *     </ProtectedRoute>
 *   );
 * }
 * ```
 */
export function ProtectedRoute({ children, loginRoute = '/login' }: ProtectedRouteProps) {
  const router = useRouter();
  const segments = useSegments();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isHydrated = useAuthStore((state) => state.isHydrated);

  useEffect(() => {
    if (!isHydrated) {
      // Wait for auth state to be hydrated before making routing decisions
      return;
    }

    // Check if current route is in an auth group (login, register, etc.)
    // Cast to string to avoid type errors with typed routes before auth routes exist
    const firstSegment = segments[0] as string;
    const inAuthGroup = firstSegment === '(auth)' || firstSegment === 'login';

    if (!isAuthenticated && !inAuthGroup) {
      // Redirect to login if not authenticated and not already in auth group
      // Using 'as any' to bypass typed routes since login route may not exist yet
      router.replace(loginRoute as any);
    } else if (isAuthenticated && inAuthGroup) {
      // Redirect to home if authenticated and in auth group (e.g., login page)
      router.replace('/');
    }
  }, [isAuthenticated, isHydrated, segments, router, loginRoute]);

  return <>{children}</>;
}

/**
 * Hook to use auth protection in any component.
 * Returns the current auth state and provides redirect logic.
 *
 * Usage:
 * ```tsx
 * const { isAuthenticated, isLoading } = useProtectedRoute();
 *
 * if (isLoading) return <Loading />;
 * if (!isAuthenticated) return null; // Will redirect
 * return <ProtectedContent />;
 * ```
 */
export function useProtectedRoute(loginRoute = '/login') {
  const router = useRouter();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isHydrated = useAuthStore((state) => state.isHydrated);

  useEffect(() => {
    if (isHydrated && !isAuthenticated) {
      // Using 'as any' to bypass typed routes since login route may not exist yet
      router.replace(loginRoute as any);
    }
  }, [isAuthenticated, isHydrated, router, loginRoute]);

  return {
    isAuthenticated,
    isLoading: !isHydrated,
  };
}
