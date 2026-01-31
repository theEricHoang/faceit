export type UserType = 'student' | 'instructor';

export interface User {
  user_id: string;
  first_name: string;
  last_name: string;
  type: UserType;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isHydrated: boolean;
}

export interface AuthActions {
  setUser: (user: User) => void;
  setTokens: (tokens: AuthTokens) => Promise<void>;
  clearAuth: () => Promise<void>;
  hydrate: () => Promise<void>;
}

export type AuthStore = AuthState & AuthActions;
