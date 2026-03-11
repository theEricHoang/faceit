import { Redirect, Stack } from 'expo-router';

import { useAuthStore } from '@/stores/auth-store';

export default function AuthLayout() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isHydrated = useAuthStore((state) => state.isHydrated);
  const needsFaceEnrollment = useAuthStore((state) => state.needsFaceEnrollment);

  // Wait for auth state to hydrate
  if (!isHydrated) {
    return null;
  }

  // Redirect authenticated users - to face enrollment if needed, otherwise home
  if (isAuthenticated) {
    return <Redirect href={needsFaceEnrollment ? "/enroll-face" : "/"} />;
  }

  return (
    <Stack
      screenOptions={{
        headerShown: false,
      }}
    >
      <Stack.Screen name="login" />
      <Stack.Screen name="register" />
      <Stack.Screen name="register-student" />
      <Stack.Screen name="register-instructor" />
    </Stack>
  );
}
