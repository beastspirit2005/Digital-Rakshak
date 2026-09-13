/**
 * Central API configuration.
 * 
 * In development: reads from NEXT_PUBLIC_API_URL in .env.local (defaults to localhost)
 * In production (Vercel): set NEXT_PUBLIC_API_URL in Vercel Environment Variables
 *   e.g. https://your-backend.railway.app/v1
 */

const isLocal = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || (isLocal ? "http://127.0.0.1:8000/v1" : "/api/v1");

import axios from 'axios';
axios.defaults.withCredentials = true;

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

/**
 * Safely extract a human-readable error message from Axios / FastAPI response errors.
 * Formats Pydantic 422 error arrays, object details, and network error messages.
 */
export function formatApiError(err: any, fallback = "An unexpected error occurred"): string {
  if (!err) return fallback;
  const detail = err.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item: any) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const loc = Array.isArray(item.loc) ? item.loc.filter((l: any) => l !== "body").join(" ") : "";
          const msg = item.msg || item.message || JSON.stringify(item);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(item);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return err.message || fallback;
}

/**
 * Helper to build WebSocket URLs matching API_BASE_URL.
 * Usage: wsApi("/transactions/ws") → "ws://127.0.0.1:8000/v1/transactions/ws"
 */
export function wsApi(path: string): string {
  const cleanPath = path.replace(/^\/api\/v1/, "").replace(/^\/v1/, "");
  const normalizedPath = cleanPath.startsWith("/") ? cleanPath : `/${cleanPath}`;

  if (typeof window !== "undefined") {
    if (API_BASE_URL.startsWith("http://") || API_BASE_URL.startsWith("https://")) {
      const wsUrl = API_BASE_URL.replace(/^http/, "ws");
      return `${wsUrl}${normalizedPath}`;
    }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/api/v1${normalizedPath}`;
  }
  return `ws://127.0.0.1:8000/v1${normalizedPath}`;
}

// Request Interceptor to attach the token automatically
axios.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      if (token && config.headers) {
        if (typeof config.headers.set === 'function') {
            config.headers.set('Authorization', `Bearer ${token}`);
        } else {
            config.headers.Authorization = `Bearer ${token}`;
        }
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Global Interceptor for Session Desync (401 Unauthorized)
// Only triggers for authenticated API calls, NOT for login/register/otp attempts
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Check if this request was to an auth endpoint — if so, DON'T intercept.
      // A 401 on /auth/login-password just means wrong credentials, not an expired session.
      const requestUrl = error.config?.url || "";
      const isAuthEndpoint = requestUrl.includes("/auth/");
      
      if (!isAuthEndpoint) {
        // This is a genuine expired-session 401 from a protected endpoint.
        // Clear the correct localStorage keys that auth-store.ts actually uses.
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        localStorage.removeItem("dr_last_activity");
        
        // Redirect to login only if not already there
        if (typeof window !== "undefined" && !window.location.pathname.includes("/auth/login")) {
          window.location.href = "/auth/login?expired=1";
        }
      }
    }
    return Promise.reject(error);
  }
);
