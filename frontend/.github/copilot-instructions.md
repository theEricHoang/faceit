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

## Experimental Features
Enabled in `app.json`:
- `typedRoutes`: Type-safe route names
- `reactCompiler`: React Compiler optimization
