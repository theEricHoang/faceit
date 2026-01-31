export type UserType = 'student' | 'instructor';

export interface User {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  type: UserType;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
}

// Login types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  type: UserType;
}

// Student signup types
export interface StudentSignupRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  bio?: string | null;
  number?: string | null;
  major?: string | null;
}

export interface StudentSignupResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  bio: string | null;
  type: UserType;
  number: string;
  major: string | null;
}

// Instructor signup types
export interface InstructorSignupRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  bio?: string | null;
  department?: string | null;
  office_location?: string | null;
}

export interface InstructorSignupResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  bio: string | null;
  type: UserType;
  department: string | null;
  office_location: string | null;
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
