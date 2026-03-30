import { supabase } from './supabase';

/**
 * API base URL — in production, points to the backend service.
 * In dev, empty string so /api calls go through Vite's proxy.
 */
export const API_BASE = import.meta.env.VITE_API_URL ?? '';

/** Prefix a path with the API base URL */
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/** Authenticated fetch — attaches Supabase JWT as Bearer token */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const { data: { session } } = await supabase.auth.getSession();
  const headers = new Headers(init?.headers);

  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`);
  }

  return fetch(apiUrl(path), { ...init, headers });
}
