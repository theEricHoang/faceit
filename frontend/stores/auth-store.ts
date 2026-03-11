import { create } from 'zustand';

import {
    clearAllTokens,
    getAccessToken,
    getRefreshToken,
    setAccessToken,
    setRefreshToken,
    getUserData,
    setUserData,
} from '@/services/secure-storage';
import type { AuthStore, AuthTokens, User } from '@/types/auth';

export const useAuthStore = create<AuthStore>((set, get) => ({
  // State
  user: null,
  isAuthenticated: false,
  isHydrated: false,
  needsFaceEnrollment: false,

  // Actions
  setUser: async (user: User) => {
    await setUserData(user);
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
    set({ user: null, isAuthenticated: false, needsFaceEnrollment: false });
  },

  setNeedsFaceEnrollment: (value: boolean) => {
    set({ needsFaceEnrollment: value });
  },

  hydrate: async () => {
    try {
      const [accessToken, refreshToken, userData] = await Promise.all([
        getAccessToken(),
        getRefreshToken(),
        getUserData(),
      ]);

      // restore auth state only if we have both tokens and user data
      if (accessToken && refreshToken && userData) {
        set({ isAuthenticated: true, isHydrated: true, user: userData });
      } else {
        set({ isAuthenticated: false, isHydrated: true, user: null });
      }
    } catch (error) {
      console.error('Failed to hydrate auth state:', error);
      set({ isAuthenticated: false, isHydrated: true, user: null });
    }
  },
}));
