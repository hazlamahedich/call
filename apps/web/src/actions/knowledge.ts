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
}

export async function uploadKnowledgeFile(formData: FormData) {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) return { error: "Not authenticated" };

  try {
    const response = await fetch(`${API_URL}/api/v1/knowledge/upload`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Upload failed" };
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
    const response = await fetch(`${API_URL}/api/v1/knowledge/upload`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url, title }),
    });

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to add URL" };
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
    const response = await fetch(`${API_URL}/api/v1/knowledge/upload`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text, title }),
    });

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to add text" };
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
  pageSize = 20
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
      `${API_URL}/api/v1/knowledge/documents?${params}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to list documents", data: null };
    }

    const data: DocumentListResponse = await response.json();
    return { data, error: null };
  } catch (error) {
    return { error: "Failed to list documents: " + (error as Error).message, data: null };
  }
}

export async function deleteKnowledgeDocument(id: number) {
  const { getToken } = await auth();
  const token = await getToken();
  if (!token) return { error: "Not authenticated" };

  try {
    const response = await fetch(`${API_URL}/api/v1/knowledge/documents/${id}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Failed to delete document" };
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
    const response = await fetch(`${API_URL}/api/v1/knowledge/search`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query, topK }),
    });

    if (!response.ok) {
      const error = await response.json();
      return { error: error.detail || "Search failed", data: null };
    }

    const data: KnowledgeSearchResponse = await response.json();
    return { data, error: null };
  } catch (error) {
    return { error: "Search failed: " + (error as Error).message, data: null };
  }
}
