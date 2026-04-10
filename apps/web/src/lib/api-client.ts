"use server";

import { auth } from "@clerk/nextjs/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

type ApiResult<T> = { data: T | null; error: string | null };

async function getAuthHeader(): Promise<{ Authorization: string } | null> {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) return null;
  return { Authorization: `Bearer ${token}` };
}

async function parseErrorResponse(
  response: Response,
  fallbackMsg: string,
): Promise<string> {
  try {
    const err = await response.json();
    return err.detail?.message || err.message || fallbackMsg;
  } catch {
    return fallbackMsg;
  }
}

async function apiRequest<T>(
  path: string,
  options: RequestInit & { fallbackError: string },
): Promise<ApiResult<T>> {
  try {
    const headers = await getAuthHeader();
    if (!headers) return { data: null, error: "Not authenticated" };

    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...headers,
        ...(options.headers || {}),
      },
    });

    if (!response.ok) {
      const errMsg = await parseErrorResponse(response, options.fallbackError);
      return { data: null, error: errMsg };
    }

    if (
      response.status === 204 ||
      response.headers.get("content-length") === "0"
    ) {
      return { data: null, error: null };
    }

    const data = await response.json();
    return { data, error: null };
  } catch (e) {
    return { data: null, error: (e as Error).message };
  }
}

function jsonHeaders(): Record<string, string> {
  return { "Content-Type": "application/json" };
}

export const apiClient = {
  get<T>(path: string, opts: { fallbackError: string }): Promise<ApiResult<T>> {
    return apiRequest<T>(path, {
      method: "GET",
      fallbackError: opts.fallbackError,
    });
  },

  post<T>(
    path: string,
    body: unknown,
    opts: { fallbackError: string },
  ): Promise<ApiResult<T>> {
    return apiRequest<T>(path, {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify(body),
      fallbackError: opts.fallbackError,
    });
  },

  patch<T>(
    path: string,
    body: unknown,
    opts: { fallbackError: string },
  ): Promise<ApiResult<T>> {
    return apiRequest<T>(path, {
      method: "PATCH",
      headers: jsonHeaders(),
      body: JSON.stringify(body),
      fallbackError: opts.fallbackError,
    });
  },

  delete(
    path: string,
    opts: { fallbackError: string },
  ): Promise<ApiResult<null>> {
    return apiRequest<null>(path, {
      method: "DELETE",
      fallbackError: opts.fallbackError,
    });
  },
};

export { apiRequest, getAuthHeader, API_URL };
export type { ApiResult };
