/**
 * API base URL — in production, points to the backend service.
 * In dev, empty string so /api calls go through Vite's proxy.
 */
export const API_BASE = import.meta.env.VITE_API_URL ?? '';

/** Prefix a path with the API base URL */
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}
