/** API client — fetch wrapper with JWT auth headers. */

import type { ApiError } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiClientError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiClientError";
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Get the access token from the session.
 * On the client side, it queries NextAuth's session endpoint.
 */
async function getAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  try {
    const res = await fetch("/api/auth/session");
    const session = await res.json();
    return session?.accessToken ?? null;
  } catch {
    return null;
  }
}

/**
 * Core fetch wrapper that appends auth headers and handles errors.
 */
async function fetchApi<T>(
  path: string,
  options: RequestInit = {},
  skipAuth = false,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (!skipAuth) {
    const token = await getAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const url = `${API_BASE_URL}${path}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = "Erro desconhecido";
    try {
      const body: ApiError = await response.json();
      detail = body.detail;
    } catch {
      detail = response.statusText;
    }
    throw new ApiClientError(response.status, detail);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// ─── Public API ────────────────────────────────────

export const api = {
  get: <T>(path: string, skipAuth = false) =>
    fetchApi<T>(path, { method: "GET" }, skipAuth),

  post: <T>(path: string, body?: unknown, skipAuth = false) =>
    fetchApi<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined }, skipAuth),

  put: <T>(path: string, body?: unknown) =>
    fetchApi<T>(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),

  delete: <T>(path: string) =>
    fetchApi<T>(path, { method: "DELETE" }),
};

export { ApiClientError, API_BASE_URL };
