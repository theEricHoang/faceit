import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import type { User } from '@/types/auth';

const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  USER_DATA: 'user_data',
} as const;

type StorageKey = (typeof STORAGE_KEYS)[keyof typeof STORAGE_KEYS];

/**
 * Get an item from secure storage
 * Falls back to localStorage on web since expo-secure-store doesn't support web
 */
async function getSecureItem(key: StorageKey): Promise<string | null> {
  if (Platform.OS === 'web') {
    return localStorage.getItem(key);
  }
  return SecureStore.getItemAsync(key);
}

/**
 * Set an item in secure storage
 * Falls back to localStorage on web since expo-secure-store doesn't support web
 */
async function setSecureItem(key: StorageKey, value: string): Promise<void> {
  if (Platform.OS === 'web') {
    localStorage.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

/**
 * Delete an item from secure storage
 * Falls back to localStorage on web since expo-secure-store doesn't support web
 */
async function deleteSecureItem(key: StorageKey): Promise<void> {
  if (Platform.OS === 'web') {
    localStorage.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

// Token-specific helpers
export async function getAccessToken(): Promise<string | null> {
  return getSecureItem(STORAGE_KEYS.ACCESS_TOKEN);
}

export async function setAccessToken(token: string): Promise<void> {
  return setSecureItem(STORAGE_KEYS.ACCESS_TOKEN, token);
}

export async function deleteAccessToken(): Promise<void> {
  return deleteSecureItem(STORAGE_KEYS.ACCESS_TOKEN);
}

export async function getRefreshToken(): Promise<string | null> {
  return getSecureItem(STORAGE_KEYS.REFRESH_TOKEN);
}

export async function setRefreshToken(token: string): Promise<void> {
  return setSecureItem(STORAGE_KEYS.REFRESH_TOKEN, token);
}

export async function deleteRefreshToken(): Promise<void> {
  return deleteSecureItem(STORAGE_KEYS.REFRESH_TOKEN);
}

// user data helpers for storing in secure storage
export async function getUserData(): Promise<User | null> {
  const data = await getSecureItem(STORAGE_KEYS.USER_DATA);
  if (!data) return null;
  try {
    return JSON.parse(data) as User;
  } catch (error) {
    console.error('Failed to parse user data from secure storage:', error);
    return null;
  }
}

export async function setUserData(user: User): Promise<void> {
  return setSecureItem(STORAGE_KEYS.USER_DATA, JSON.stringify(user));
}

export async function deleteUserData(): Promise<void> {
  return deleteSecureItem(STORAGE_KEYS.USER_DATA);
}

export async function clearAllTokens(): Promise<void> {
  await Promise.all([deleteAccessToken(), deleteRefreshToken(), deleteUserData()]);
}
