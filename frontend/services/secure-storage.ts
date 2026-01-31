import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const TOKEN_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
} as const;

type TokenKey = (typeof TOKEN_KEYS)[keyof typeof TOKEN_KEYS];

/**
 * Get an item from secure storage
 * Falls back to localStorage on web since expo-secure-store doesn't support web
 */
async function getSecureItem(key: TokenKey): Promise<string | null> {
  if (Platform.OS === 'web') {
    return localStorage.getItem(key);
  }
  return SecureStore.getItemAsync(key);
}

/**
 * Set an item in secure storage
 * Falls back to localStorage on web since expo-secure-store doesn't support web
 */
async function setSecureItem(key: TokenKey, value: string): Promise<void> {
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
async function deleteSecureItem(key: TokenKey): Promise<void> {
  if (Platform.OS === 'web') {
    localStorage.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

// Token-specific helpers
export async function getAccessToken(): Promise<string | null> {
  return getSecureItem(TOKEN_KEYS.ACCESS_TOKEN);
}

export async function setAccessToken(token: string): Promise<void> {
  return setSecureItem(TOKEN_KEYS.ACCESS_TOKEN, token);
}

export async function deleteAccessToken(): Promise<void> {
  return deleteSecureItem(TOKEN_KEYS.ACCESS_TOKEN);
}

export async function getRefreshToken(): Promise<string | null> {
  return getSecureItem(TOKEN_KEYS.REFRESH_TOKEN);
}

export async function setRefreshToken(token: string): Promise<void> {
  return setSecureItem(TOKEN_KEYS.REFRESH_TOKEN, token);
}

export async function deleteRefreshToken(): Promise<void> {
  return deleteSecureItem(TOKEN_KEYS.REFRESH_TOKEN);
}

export async function clearAllTokens(): Promise<void> {
  await Promise.all([deleteAccessToken(), deleteRefreshToken()]);
}
