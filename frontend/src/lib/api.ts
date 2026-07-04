/**
 * Central API configuration.
 * 
 * In development: reads from NEXT_PUBLIC_API_URL in .env.local (defaults to localhost)
 * In production (Vercel): set NEXT_PUBLIC_API_URL in Vercel Environment Variables
 *   e.g. https://your-backend.railway.app/api/v1
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

/**
 * Helper to build full API URLs.
 * Usage: api("/cases/my") → "http://127.0.0.1:8000/api/v1/cases/my"
 */
export function api(path: string): string {
  // Remove leading /api/v1 if someone accidentally includes it
  const cleanPath = path.replace(/^\/api\/v1/, "");
  // Ensure single leading slash
  const normalizedPath = cleanPath.startsWith("/") ? cleanPath : `/${cleanPath}`;
  return `${API_BASE_URL}${normalizedPath}`;
}
