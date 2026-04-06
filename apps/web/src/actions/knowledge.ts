"use server";

import { auth } from "@clerk/nextjs/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface KnowledgeBase {
  id: number;
  orgId: string;
  title: string;
  sourceType: "pdf" | "url" | "text";
  sourceUrl?: string;
  filePath?: string;
  fileStorageUrl?: string;
  contentHash?: string;
  chunkCount: number;
  status: "processing" | "ready" | "failed";
  errorMessage?: string;
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentListResponse {
  items: KnowledgeBase[];
  total: number;
  page: number;
  pageSize: number;
}

export interface UploadResponse {
  knowledgeBaseId: number;
  status: "processing" | "ready" | "failed";
  message: string;
}

export interface KnowledgeSearchResult {
  chunkId: number;
  knowledgeBaseId: number;
  content: string;
  metadata?: Record<string, unknown>;
  similarity: number;
}

export interface KnowledgeSearchResponse {
  results: KnowledgeSearchResult[];
  total: number;
  query: string;
  guardOverheadMs?: number;
}

function isNamespaceViolation(detail: unknown): boolean {
  if (typeof detail === "object" && detail !== null) {
    const obj = detail as Record<string, unknown>;
    return obj.code === "NAMESPACE_VIOLATION";
  }
  return false;
}

function extractErrorMessage(
  response: Response,
  body: unknown,
  fallback: string,
): string {
  if (response.status === 403) {
    const detail = body;
    if (isNamespaceViolation(detail)) {
      return "Access denied: This resource belongs to a different organization.";
    }
    return "You do not have permission to access this resource.";
  }
  if (typeof body === "object" && body !== null) {
    const obj = body as Record<string, unknown>;
    if (typeof obj.detail === "string") return obj.detail;
    if (typeof obj.message === "string") return obj.message;
  }
  return fallback;
}

export async function uploadKnowledgeFile(formData: FormData) {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) return { error: "Not authenticated" };

  try {
    const response = await fetch(`${API_URL}/api/knowledge/upload`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const body = await response.json();
      return { error: extractErrorMessage(response, body, "Upload failed") };
    }

    const data: UploadResponse = await response.json();
    return { data, error: null };
  } catch (error) {
    return { error: "Upload failed: " + (error as Error).message };
  }
}

export async function addKnowledgeUrl(url: string, title?: string) {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) return { error: "Not authenticated" };

  try {
    const response = await fetch(`${API_URL}/api/knowledge/upload`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url, title }),
    });

    if (!response.ok) {
      const body = await response.json();
      return {
        error: extractErrorMessage(response, body, "Failed to add URL"),
      };
    }

    const data: UploadResponse = await response.json();
    return { data, error: null };
  } catch (error) {
    return { error: "Failed to add URL: " + (error as Error).message };
  }
}

export async function addKnowledgeText(text: string, title?: string) {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) return { error: "Not authenticated" };

  try {
    const response = await fetch(`${API_URL}/api/knowledge/upload`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text, title }),
    });

    if (!response.ok) {
      const body = await response.json();
      return {
        error: extractErrorMessage(response, body, "Failed to add text"),
      };
    }

    const data: UploadResponse = await response.json();
    return { data, error: null };
  } catch (error) {
    return { error: "Failed to add text: " + (error as Error).message };
  }
}

export async function listKnowledgeDocuments(
  status?: "processing" | "ready" | "failed",
  page = 1,
  pageSize = 20,
) {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) return { error: "Not authenticated", data: null };

  try {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });

    if (status) {
      params.set("status_filter", status);
    }

    const response = await fetch(
      `${API_URL}/api/knowledge/documents?${params}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    );

    if (!response.ok) {
      const body = await response.json();
      return {
        error: extractErrorMessage(response, body, "Failed to list documents"),
        data: null,
      };
    }

    const data: DocumentListResponse = await response.json();
    return { data, error: null };
  } catch (error) {
    return {
      error: "Failed to list documents: " + (error as Error).message,
      data: null,
    };
  }
}

export async function deleteKnowledgeDocument(id: number) {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) return { error: "Not authenticated" };

  try {
    const response = await fetch(`${API_URL}/api/knowledge/documents/${id}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const body = await response.json();
      return {
        error: extractErrorMessage(response, body, "Failed to delete document"),
      };
    }

    return { error: null };
  } catch (error) {
    return { error: "Failed to delete document: " + (error as Error).message };
  }
}

export async function searchKnowledge(query: string, topK = 5) {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) return { error: "Not authenticated", data: null };

  try {
    const response = await fetch(`${API_URL}/api/knowledge/search`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query, topK }),
    });

    if (!response.ok) {
      const body = await response.json();
      return {
        error: extractErrorMessage(response, body, "Search failed"),
        data: null,
      };
    }

    const data: KnowledgeSearchResponse = await response.json();
    return { data, error: null };
  } catch (error) {
    return { error: "Search failed: " + (error as Error).message, data: null };
  }
}
