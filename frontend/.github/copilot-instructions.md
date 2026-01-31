# Copilot Instructions for FaceIt Frontend

## Project Overview
Expo/React Native mobile app (SDK 54) using file-based routing with `expo-router`. Targets iOS, Android, and web with React 19 and the new architecture enabled.

## Architecture

### File-Based Routing (`app/`)
- **`app/_layout.tsx`**: Root layout with `ThemeProvider` and `Stack` navigator
- **`app/(tabs)/`**: Tab group with bottom navigation (Home, Explore)
- **Route groups** use `(parentheses)` naming - they organize routes without affecting URL paths
- Modals use `presentation: 'modal'` in `Stack.Screen` options

### Component Structure
| Directory | Purpose |
|-----------|---------|
| `components/` | Reusable UI components |
| `components/ui/` | Primitive UI elements (icons, collapsibles) |
| `constants/` | Theme colors, fonts |
| `hooks/` | Custom React hooks |

### Theming Pattern
Use themed components instead of raw React Native primitives:
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

### Platform-Specific Files
Use `.ios.tsx` suffix for iOS-specific implementations:
- `icon-symbol.tsx` - Android/web fallback (MaterialIcons)
- `icon-symbol.ios.tsx` - iOS native (SF Symbols via expo-symbols)

When adding icons, map SF Symbol names to Material Icons in `MAPPING` object in `icon-symbol.tsx`.

## Key Conventions

### Imports
Use the `@/` path alias for absolute imports:
```tsx
import { Colors } from '@/constants/theme';
import { useColorScheme } from '@/hooks/use-color-scheme';
```

### Naming
- **Files**: `kebab-case.tsx` (e.g., `themed-text.tsx`, `haptic-tab.tsx`)
- **Components**: `PascalCase` exports (e.g., `ThemedText`, `HapticTab`)
- **Hooks**: `use-kebab-case.ts` with `useCamelCase` exports

### ThemedText Types
Available typography variants: `'default' | 'title' | 'defaultSemiBold' | 'subtitle' | 'link'`

## Authentication & API

### Auth Architecture
| Directory | Purpose |
|-----------|---------|
| `stores/` | Zustand stores for global state |
| `services/` | API client, auth service, secure storage |
| `types/` | TypeScript interfaces and types |

### Auth Store (`stores/auth-store.ts`)
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

### User Type
```tsx
type UserType = 'student' | 'instructor';

interface User {
  user_id: string;    // UUID
  first_name: string;
  last_name: string;
  type: UserType;
}
```

### API Client (`services/api-client.ts`)
Always use `apiClient` for API calls — it handles auth headers and token refresh automatically:
```tsx
import { apiClient } from '@/services/api-client';

// GET request
const data = await apiClient.get<ResponseType>('/endpoint');

// POST request
const result = await apiClient.post<ResponseType>('/endpoint', { body: 'data' });

// PUT, PATCH, DELETE
await apiClient.put<T>('/endpoint', body);
await apiClient.patch<T>('/endpoint', body);
await apiClient.delete<T>('/endpoint');

// Skip auth for public endpoints
await apiClient.post('/auth/login', credentials, { skipAuth: true });
```

**Features:**
- Auto-injects `Authorization: Bearer` header from stored access token
- On 401 response: attempts token refresh via `POST /auth/refresh`, retries original request
- On refresh failure: clears auth state (triggers redirect to login)
- Base URL from `EXPO_PUBLIC_API_URL` env variable

### Auth Service (`services/auth-service.ts`)
```tsx
import { login, logout } from '@/services/auth-service';

// Login - stores tokens automatically
const tokens = await login({ email, password });

// Logout - clears tokens and auth state
await logout();
```

### Protected Routes
Wrap protected layouts with `ProtectedRoute`:
```tsx
// In app/(protected)/_layout.tsx
import { ProtectedRoute } from '@/components/protected-route';

export default function ProtectedLayout() {
  return (
    <ProtectedRoute>
      <Stack />
    </ProtectedRoute>
  );
}
```

Or use the hook for custom protection logic:
```tsx
import { useProtectedRoute } from '@/components/protected-route';

function MyScreen() {
  const { isAuthenticated, isLoading } = useProtectedRoute();
  if (isLoading) return <Loading />;
  // ...
}
```

### Secure Storage (`services/secure-storage.ts`)
Low-level token storage (prefer using auth store/service instead):
```tsx
import { getAccessToken, setAccessToken, clearAllTokens } from '@/services/secure-storage';
```

## Commands
```bash
npx expo start          # Start dev server (press i/a/w for platform)
npm run ios             # iOS simulator
npm run android         # Android emulator
npm run web             # Web browser
npm run lint            # ESLint check
npm run reset-project   # Move app/ to app-example/, create fresh app/
```

## Dependencies to Know
- **expo-router**: File-based navigation
- **expo-haptics**: Tactile feedback (iOS tabs)
- **react-native-reanimated**: Animations (parallax scroll)
- **expo-image**: Optimized image component (prefer over `Image` from react-native)
- **@expo/vector-icons**: Icon library (MaterialIcons fallback)
- **zustand**: Global state management (auth store)
- **expo-secure-store**: Secure token storage (iOS Keychain, Android Keystore)

## Experimental Features
Enabled in `app.json`:
- `typedRoutes`: Type-safe route names
- `reactCompiler`: React Compiler optimization
