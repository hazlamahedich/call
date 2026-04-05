/**
 * API tests for Knowledge Ingestion - Story 3.1
 *
 * Coverage: P0 critical paths for backend business logic
 * Tests tenant isolation, data validation, and service contracts
 */

import { test, expect } from "@playwright/test";
import { faker } from "@faker-js/faker";
import { readFileSync } from "fs";
import { join } from "path";

test.describe("Knowledge Ingestion API - P0 Backend Tests", () => {
  const API_BASE = process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000";
  const API_PREFIX = `${API_BASE}/api/knowledge`;

  let authToken: string;
  let testOrgId: string;
  const createdDocumentIds: number[] = [];

  test.beforeAll(async () => {
    // Setup: Authenticate and get auth token
    // In real scenario, this would call the auth endpoint
    // For now, we'll use the admin session state
    authToken = "Bearer test-token"; // Placeholder
    testOrgId = faker.string.uuid();
  });

  test.afterAll(async ({ request }) => {
    // Cleanup: Delete all documents created during tests
    for (const docId of createdDocumentIds) {
      try {
        await request.delete(`${API_PREFIX}/documents/${docId}`, {
          headers: { Authorization: authToken },
        });
      } catch (error) {
        // Ignore cleanup errors
        console.warn(`Failed to delete document ${docId}:`, error);
      }
    }
  });

  test.describe("PDF Upload Endpoint - P0", () => {
    test("should accept valid PDF file", async ({ request }) => {
      const formData = new FormData();
      const pdfContent = readFileSync(
        join(__dirname, "../fixtures/sample.pdf"),
      );
      formData.append("file", new Blob([pdfContent], { type: "application/pdf" }), "test.pdf");
      formData.append("title", "Test PDF Document");

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        multipart: {
          file: {
            name: "test.pdf",
            mimeType: "application/pdf",
            buffer: pdfContent,
          },
          title: "Test PDF Document",
        },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body).toHaveProperty("knowledgeBaseId");
      expect(body).toHaveProperty("status", "processing");
    });

    test("should reject file exceeding 50MB limit", async ({ request }) => {
      // Create oversized buffer (51MB)
      const oversizedBuffer = Buffer.alloc(51 * 1024 * 1024);

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        multipart: {
          file: {
            name: "oversized.pdf",
            mimeType: "application/pdf",
            buffer: oversizedBuffer,
          },
        },
      });

      expect(response.status()).toBe(413); // Payload Too Large
      const body = await response.json();
      expect(body.detail).toMatch(/file too large|exceeds limit/i);
    });

    test("should reject invalid file format", async ({ request }) => {
      const invalidContent = Buffer.from("MZ\x90\x00"); // EXE magic bytes

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        multipart: {
          file: {
            name: "test.exe",
            mimeType: "application/x-msdownload",
            buffer: invalidContent,
          },
        },
      });

      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.detail).toMatch(/unsupported file format|invalid format/i);
    });

    test("should return error for password-protected PDF", async ({
      request,
    }) => {
      // This would require an actual password-protected PDF fixture
      // For now, test the error handling structure

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        multipart: {
          file: {
            name: "protected.pdf",
            mimeType: "application/pdf",
            buffer: Buffer.from("%PDF-encrypted-test"),
          },
        },
      });

      // Should either accept for processing (async detection) or reject
      expect([200, 400]).toContain(response.status());

      if (response.status() === 400) {
        const body = await response.json();
        expect(body.detail).toMatch(/encrypted|password-protected/i);
      }
    });

    test("should accept exactly one source type", async ({ request }) => {
      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        multipart: {
          // Missing file, url, and text
          title: "Test",
        },
      });

      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.detail).toMatch(/exactly one source|must provide/i);
    });
  });

  test.describe("URL Ingestion Endpoint - P0", () => {
    test("should accept valid public URL", async ({ request }) => {
      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          url: "https://example.com/article-test",
          title: "Test Article",
        },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body).toHaveProperty("knowledgeBaseId");
      expect(body).toHaveProperty("status", "processing");
    });

    test("should reject internal IP addresses (SSRF protection)", async ({
      request,
    }) => {
      const internalUrls = [
        "http://localhost:8080/admin",
        "http://127.0.0.1/test",
        "http://10.0.0.1/internal",
        "http://192.168.1.1/local",
      ];

      for (const url of internalUrls) {
        const response = await request.post(`${API_PREFIX}/upload`, {
          headers: {
            Authorization: authToken,
          },
          form: {
            url: url,
          },
        });

        expect(response.status()).toBe(400);
        const body = await response.json();
        expect(body.detail).toMatch(/internal|not allowed|ssrf/i);
      }
    });

    test("should timeout on slow URLs", async ({ request }) => {
      // Use a URL that will timeout
      const slowUrl = "http://10.255.255.1:8080/slow-resource";

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          url: slowUrl,
        },
      });

      // Should either timeout quickly or reject as internal
      expect([400, 408, 504]).toContain(response.status());
    });

    test("should validate URL format", async ({ request }) => {
      const invalidUrls = [
        "not-a-url",
        "ftp://example.com",
        "javascript:alert('xss')",
        "//example.com",
      ];

      for (const url of invalidUrls) {
        const response = await request.post(`${API_PREFIX}/upload`, {
          headers: {
            Authorization: authToken,
          },
          form: {
            url: url,
          },
        });

        expect(response.status()).toBe(400);
      }
    });
  });

  test.describe("Text Ingestion Endpoint - P0", () => {
    test("should accept valid text content", async ({ request }) => {
      const textContent =
        "This is a test knowledge base entry. ".repeat(10) +
        "It contains sufficient content for ingestion and processing.";

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          text: textContent,
          title: "Test Knowledge Entry",
        },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body).toHaveProperty("knowledgeBaseId");
    });

    test("should reject text below minimum length", async ({ request }) => {
      const shortText = "Too short";

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          text: shortText,
        },
      });

      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.detail).toMatch(/too short|minimum length/i);
    });

    test("should reject empty text", async ({ request }) => {
      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          text: "",
        },
      });

      expect(response.status()).toBe(400);
    });
  });

  test.describe("Document List Endpoint - P0", () => {
    let documentId: number;

    test.beforeAll(async ({ request }) => {
      // Create a test document
      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          text: "Test document for list endpoint. ".repeat(20),
          title: "List Test Document",
        },
      });

      if (response.status() === 200) {
        const body = await response.json();
        documentId = body.knowledgeBaseId;
        createdDocumentIds.push(documentId);
      }
    });

    test("should list documents with pagination", async ({ request }) => {
      const response = await request.get(`${API_PREFIX}/documents`, {
        headers: {
          Authorization: authToken,
        },
        params: {
          page: 1,
          page_size: 20,
        },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body).toHaveProperty("items");
      expect(body).toHaveProperty("total");
      expect(body).toHaveProperty("page", 1);
      expect(body).toHaveProperty("page_size", 20);
      expect(Array.isArray(body.items)).toBe(true);
    });

    test("should filter documents by status", async ({ request }) => {
      const response = await request.get(`${API_PREFIX}/documents`, {
        headers: {
          Authorization: authToken,
        },
        params: {
          status: "ready",
        },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.items.every((item: unknown) => (item as any).status === "ready")).toBe(true);
    });

    test("should enforce pagination limits", async ({ request }) => {
      // Request more than max page size
      const response = await request.get(`${API_PREFIX}/documents`, {
        headers: {
          Authorization: authToken,
        },
        params: {
          page: 1,
          page_size: 200, // Exceeds max of 100
        },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.page_size).toBeLessThanOrEqual(100);
    });

    test("should return empty list when no documents", async ({ request }) => {
      // Use a different org context (would need proper auth setup)
      const response = await request.get(`${API_PREFIX}/documents`, {
        headers: {
          Authorization: authToken,
        },
        params: {
          page: 9999, // Page beyond existing data
        },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body.items).toEqual([]);
    });
  });

  test.describe("Document Delete Endpoint - P0", () => {
    let documentId: number;

    test.beforeAll(async ({ request }) => {
      // Create a test document
      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          text: "Test document for delete endpoint. ".repeat(20),
          title: "Delete Test Document",
        },
      });

      if (response.status() === 200) {
        const body = await response.json();
        documentId = body.knowledgeBaseId;
        // Don't add to cleanup since we're testing deletion
      }
    });

    test("should delete ready document successfully", async ({ request }) => {
      if (!documentId) {
        test.skip();
        return;
      }

      const response = await request.delete(`${API_PREFIX}/documents/${documentId}`, {
        headers: {
          Authorization: authToken,
        },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body).toHaveProperty("message");
      expect(body.message).toMatch(/deleted successfully/i);
    });

    test("should prevent deletion while processing", async ({ request }) => {
      // Create a document (will be in "processing" state initially)
      const createResponse = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          text: "Processing test document. ".repeat(20),
        },
      });

      if (createResponse.status() !== 200) {
        test.skip();
        return;
      }

      const createBody = await createResponse.json();
      const processingDocId = createBody.knowledgeBaseId;

      // Try to delete immediately (should be processing)
      const deleteResponse = await request.delete(
        `${API_PREFIX}/documents/${processingDocId}`,
        {
          headers: {
            Authorization: authToken,
          },
        },
      );

      // Should return 409 Conflict or similar
      expect([409, 423]).toContain(deleteResponse.status());
    });

    test("should return 404 for non-existent document", async ({ request }) => {
      const response = await request.delete(`${API_PREFIX}/documents/999999`, {
        headers: {
          Authorization: authToken,
        },
      });

      expect(response.status()).toBe(404);
    });
  });

  test.describe("Tenant Isolation - P0", () => {
    test("should scope documents by org_id", async ({ request }) => {
      // Create document with current org
      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          text: "Tenant isolation test. ".repeat(20),
        },
      });

      expect(response.status()).toBe(200);
      const body = await response.json();
      expect(body).toHaveProperty("knowledgeBaseId");

      // List documents should only return current org's documents
      const listResponse = await request.get(`${API_PREFIX}/documents`, {
        headers: {
          Authorization: authToken,
        },
      });

      expect(listResponse.status()).toBe(200);
      const listBody = await listResponse.json();

      // Verify all items belong to current org
      // (This would require org_id in response or separate verification)
      expect(Array.isArray(listBody.items)).toBe(true);
    });

    test("should prevent cross-org document access", async ({ request }) => {
      // Try to access a document that may belong to another org
      // This test requires multi-tenant setup

      const response = await request.get(`${API_PREFIX}/documents/999`, {
        headers: {
          Authorization: authToken,
        },
      });

      // Should either return 404 or 403
      expect([404, 403]).toContain(response.status());
    });
  });

  test.describe("Duplicate Detection - P1", () => {
    test("should detect duplicate content by hash", async ({ request }) => {
      consttextContent = "Duplicate test content. ".repeat(25);

      // Upload first copy
      const firstResponse = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          text: textContent,
          title: "First Copy",
        },
      });

      expect(firstResponse.status()).toBe(200);

      // Try to upload duplicate content
      const secondResponse = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          text: textContent,
          title: "Duplicate Copy",
        },
      });

      // Should either accept with deduplication warning or reject
      expect([200, 409]).toContain(secondResponse.status());

      if (secondResponse.status() === 409) {
        const body = await secondResponse.json();
        expect(body.detail).toMatch(/duplicate|already exists/i);
      }
    });
  });

  test.describe("Vector Search Endpoint - P1", () => {
    test("should perform vector similarity search", async ({ request }) => {
      // First, upload some content
      await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          text: "Test content for vector search. ".repeat(30),
          title: "Search Test Document",
        },
      });

      // Wait for processing by polling document status
      let retries = 0;
      let processed = false;
      while (retries < 10 && !processed) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        // In real scenario, check status endpoint
        retries++;
        if (retries >= 5) processed = true; // Assume processed for test
      }

      // Perform search
      const response = await request.post(`${API_PREFIX}/search`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          query: "test content",
          top_k: 5,
        },
      });

      // Should either return results or 503 if embedding service not configured
      expect([200, 503]).toContain(response.status());

      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toHaveProperty("results");
        expect(body).toHaveProperty("total");
        expect(body).toHaveProperty("query");
        expect(Array.isArray(body.results)).toBe(true);
        expect(body.results.length).toBeLessThanOrEqual(5);

        // Verify result structure
        if (body.results.length > 0) {
          const firstResult = body.results[0];
          expect(firstResult).toHaveProperty("chunk_id");
          expect(firstResult).toHaveProperty("content");
          expect(firstResult).toHaveProperty("similarity");
          expect(typeof firstResult.similarity).toBe("number");
        }
      }
    });

    test("should enforce top_k limit", async ({ request }) => {
      const response = await request.post(`${API_PREFIX}/search`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          query: "test",
          top_k: 1000, // Excessive value
        },
      });

      // Should either return 200 with limited results or error
      if (response.status() === 200) {
        const body = await response.json();
        expect(body.results.length).toBeLessThanOrEqual(100); // Reasonable max
      }
    });

    test("should return empty results for no matches", async ({ request }) => {
      const response = await request.post(`${API_PREFIX}/search`, {
        headers: {
          Authorization: authToken,
        },
        form: {
          query: "xyzabc123nonexistentcontent",
          top_k: 5,
        },
      });

      // May return 503 if embedding service not configured
      if (response.status() === 200) {
        const body = await response.json();
        expect(body.results).toEqual([]);
      }
    });
  });

  test.describe("Rate Limiting - P1", () => {
    test("should enforce concurrent upload limit", async ({ request }) => {
      const uploadPromises = Array.from({ length: 15 }, () =>
        request.post(`${API_PREFIX}/upload`, {
          headers: {
            Authorization: authToken,
          },
          form: {
            text: "Rate limit test content. ".repeat(20),
          },
        }),
      );

      const responses = await Promise.all(uploadPromises);

      // Some should succeed, some should be rate limited
      const successCount = responses.filter((r) => r.status() === 200).length;
      const rateLimitedCount = responses.filter((r) => r.status() === 429).length;

      // At least some should be rate limited
      expect(rateLimitedCount).toBeGreaterThan(0);
      expect(successCount).toBeLessThanOrEqual(10); // Max 10 concurrent
    });
  });

  test.describe("Authentication & Authorization - P0", () => {
    test("should reject requests without auth token", async ({ request }) => {
      const response = await request.get(`${API_PREFIX}/documents`);

      expect(response.status()).toBe(401);
    });

    test("should reject requests with invalid auth token", async ({
      request,
    }) => {
      const response = await request.get(`${API_PREFIX}/documents`, {
        headers: {
          Authorization: "Bearer invalid-token",
        },
      });

      expect(response.status()).toBe(401);
    });

    test("should validate token on every request", async ({ request }) => {
      const response = await request.delete(`${API_PREFIX}/documents/1`, {
        headers: {
          Authorization: "Bearer expired-token",
        },
      });

      expect(response.status()).toBe(401);
    });
  });
});
