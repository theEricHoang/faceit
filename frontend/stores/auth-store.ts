import { create } from 'zustand';

import {
    clearAllTokens,
    getAccessToken,
    getRefreshToken,
    setAccessToken,
    setRefreshToken,
} from '@/services/secure-storage';
import type { AuthStore, AuthTokens, User } from '@/types/auth';

export const useAuthStore = create<AuthStore>((set, get) => ({
  // State
  user: null,
  isAuthenticated: false,
  isHydrated: false,

  // Actions
  setUser: (user: User) => {
    set({ user, isAuthenticated: true });
  },

  setTokens: async (tokens: AuthTokens) => {
    await Promise.all([
      setAccessToken(tokens.access_token),
      setRefreshToken(tokens.refresh_token),
    ]);
    set({ isAuthenticated: true });
  },

  clearAuth: async () => {
    await clearAllTokens();
    set({ user: null, isAuthenticated: false });
  },

  hydrate: async () => {
    try {
      const accessToken = await getAccessToken();
      const refreshToken = await getRefreshToken();

      // If we have both tokens, consider the user authenticated
      // The actual user data will be fetched separately
      if (accessToken && refreshToken) {
        set({ isAuthenticated: true, isHydrated: true });
      } else {
        set({ isAuthenticated: false, isHydrated: true });
      }
    } catch (error) {
      console.error('Failed to hydrate auth state:', error);
      set({ isAuthenticated: false, isHydrated: true });
    }
  },
}));
