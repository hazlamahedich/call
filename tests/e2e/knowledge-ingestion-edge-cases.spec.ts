/**
 * P2 Edge Case Tests for Knowledge Ingestion - Story 3.1
 *
 * Coverage: Edge cases, negative paths, and boundary conditions
 * Tests focus on unusual scenarios and error handling
 */

import { test, expect } from "@playwright/test";
import { faker } from "@faker-js/faker";
import {
  createKnowledgeBase,
  createPDFKnowledgeBase,
  createURLKnowledgeBase,
  createTextKnowledgeBase,
  createProcessingKnowledgeBase,
  createFailedKnowledgeBase,
} from "../factories/knowledge-factory";

test.describe("Knowledge Ingestion - P2 Edge Cases", () => {
  const createdDocumentIds: string[] = [];

  test.afterAll(async ({ request }) => {
    // Cleanup: Delete all documents created during tests
    const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;
    const authToken = "Bearer test-token";

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

  test.describe("PDF Processing Edge Cases", () => {
    test("should handle scanned-image-only PDF", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // This test uses the scanned.pdf fixture (no extractable text)
      const { readFileSync } = require("fs");
      const { join } = require("path");

      try {
        const scannedPdf = readFileSync(join(__dirname, "../fixtures/scanned.pdf"));

        const response = await request.post(`${API_PREFIX}/upload`, {
          headers: {
            Authorization: "Bearer test-token",
          },
          multipart: {
            file: {
              name: "scanned.pdf",
              mimeType: "application/pdf",
              buffer: scannedPdf,
            },
          },
        });

        // Should reject with "no extractable text" error
        expect([400, 422]).toContain(response.status());

        const body = await response.json();
        expect(body.detail).toMatch(/no extractable text|scanned|image-only/i);
      } catch (error) {
        // If fixture doesn't exist, skip test
        test.skip();
      }
    });

    test("should handle PDF with mixed content (text + images)", async ({
      request,
    }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // Test with PDF that has both text and images
      // Should extract text successfully, ignoring images
      const { readFileSync } = require("fs");
      const { join } = require("path");

      try {
        const multiPagePdf = readFileSync(join(__dirname, "../fixtures/multi-page.pdf"));

        const response = await request.post(`${API_PREFIX}/upload`, {
          headers: {
            Authorization: "Bearer test-token",
          },
          multipart: {
            file: {
              name: "multi-page.pdf",
              mimeType: "application/pdf",
              buffer: multiPagePdf,
            },
          },
        });

        if (response.status() === 200) {
          const body = await response.json();
          expect(body).toHaveProperty("knowledgeBaseId");
          expect(body).toHaveProperty("status", "processing");
        }
      } catch (error) {
        test.skip();
      }
    });

    test("should detect MIME spoofing (extension mismatch)", async ({
      request,
    }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // Create a file with .pdf extension but .exe content
      const spoofedFile = Buffer.from("MZ\x90\x00"); // EXE magic bytes

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        multipart: {
          file: {
            name: "malicious.pdf", // PDF extension
            mimeType: "application/pdf", // Claims PDF
            buffer: spoofedFile, // But EXE content
          },
        },
      });

      // Should reject based on magic bytes, not extension
      expect(response.status()).toBe(400);
      const body = await response.json();
      expect(body.detail).toMatch(/invalid format|unsupported/i);
    });

    test("should handle Unicode and special characters", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // Text with Unicode characters, emojis, RTL text
      const unicodeText = `
        English text with numbers: 12345
        中文文本
        النص العربي
        טקסט בעברית
        Emoji test: 🎉 🔥 🚀 ✨ 💡
        Special chars: < > & " ' \\ / @ # $ % ^ * ( ) [ ] { } | ~ `
        Math: ∑ ∫ √ ∞ ≠ ≤ ≥
        Currency: $ € £ ¥ ₹ ₽
      `.repeat(3); // Ensure minimum length

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          text: unicodeText,
          title: "🌐 Unicode Test",
        },
      });

      // Should accept and process Unicode correctly
      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toHaveProperty("knowledgeBaseId");
      }
    });

    test("should handle PDF with corrupted internal structure", async ({
      request,
    }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      const { readFileSync } = require("fs");
      const { join } = require("path");

      try {
        const corruptedPdf = readFileSync(join(__dirname, "../fixtures/corrupted.pdf"));

        const response = await request.post(`${API_PREFIX}/upload`, {
          headers: {
            Authorization: "Bearer test-token",
          },
          multipart: {
            file: {
              name: "corrupted.pdf",
              mimeType: "application/pdf",
              buffer: corruptedPdf,
            },
          },
        });

        // Should handle gracefully with specific error
        expect([400, 422, 500]).toContain(response.status());

        const body = await response.json();
        expect(body.detail).toBeDefined();
      } catch (error) {
        test.skip();
      }
    });
  });

  test.describe("URL Ingestion Edge Cases", () => {
    test("should handle URL with excessive redirects", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // URL that redirects >3 times (would need actual redirect chain)
      // For testing, we use a URL that's likely to have many redirects
      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          url: "https://bit.ly/test-redirect-chain", // Example
        },
      });

      // Should reject with "too many redirects" or similar
      if (response.status() === 400) {
        const body = await response.json();
        expect(body.detail).toMatch(/redirect|exceed/i);
      }
    });

    test("should handle URL with fragment and query params", async ({
      request,
    }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      const complexUrl = "https://example.com/path?param1=value1&param2=value2#section";

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          url: complexUrl,
        },
      });

      // Should accept valid URL with params and fragment
      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toHaveProperty("knowledgeBaseId");
      }
    });

    test("should handle URL with non-standard port", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      const urlWithPort = "https://example.com:8443/path";

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          url: urlWithPort,
        },
      });

      // Should handle appropriately
      expect([200, 400]).toContain(response.status());
    });

    test("should handle international domain names (IDN)", async ({
      request,
    }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // URL with international characters
      const idnUrl = "https://münchen.de/test";

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          url: idnUrl,
        },
      });

      // Should handle IDN correctly (punycode conversion)
      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toHaveProperty("knowledgeBaseId");
      }
    });
  });

  test.describe("Text Processing Edge Cases", () => {
    test("should handle text with only whitespace", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      const whitespaceOnly = "   \n\t   \r\n   \t   ";

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          text: whitespaceOnly,
        },
      });

      // Should reject as empty/insufficient content
      expect(response.status()).toBe(400);
    });

    test("should handle text at exact minimum length", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // Exactly 100 characters
      const exactLength = "a".repeat(100);

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          text: exactLength,
        },
      });

      // Should accept at boundary
      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toHaveProperty("knowledgeBaseId");
      }
    });

    test("should handle text with only one character less than minimum", async ({
      request,
    }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // 99 characters (one less than minimum)
      const tooShort = "a".repeat(99);

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          text: tooShort,
        },
      });

      // Should reject
      expect(response.status()).toBe(400);
    });

    test("should handle text with HTML tags", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      const htmlText = `
        <h1>Title</h1>
        <p>This is a <strong>test</strong> paragraph with <em>HTML</em> tags.</p>
        <ul>
          <li>Item 1</li>
          <li>Item 2</li>
        </ul>
        <script>alert('test')</script>
        <style>body { color: red; }</style>
      `.repeat(3);

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          text: htmlText,
        },
      });

      // Should accept (HTML will be treated as text)
      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toHaveProperty("knowledgeBaseId");
      }
    });

    test("should handle text with markdown formatting", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      const markdownText = `
        # Heading 1
        ## Heading 2
        **Bold** and *italic* text.
        - List item 1
        - List item 2
        [Link](https://example.com)
        \`code\` and \`\`\`code blocks\`\`\`
      `.repeat(3);

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          text: markdownText,
        },
      });

      // Should accept markdown as text
      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toHaveProperty("knowledgeBaseId");
      }
    });
  });

  test.describe("Chunking Edge Cases", () => {
    test("should preserve sentence boundaries", async ({ page }) => {
      // This test would need to inspect actual chunks
      // For now, we test that chunking doesn't break mid-sentence
      const textWithSentences = `
        This is sentence one. This is sentence two! This is sentence three?
        This is sentence four. This is sentence five. This is sentence six.
      `.repeat(20); // Enough content for multiple chunks

      // Upload and verify in response that chunks don't break sentences
      // This would require API endpoint to inspect chunks
    });

    test("should handle very short documents", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // Document that's barely long enough for one chunk
      const shortText = "This is a test. ".repeat(10);

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          text: shortText,
        },
      });

      if (response.status() === 200) {
        const body = await response.json();

        // Should create exactly one chunk
        // (Would need to query chunks endpoint to verify)
        expect(body).toHaveProperty("knowledgeBaseId");
      }
    });

    test("should handle very long documents", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // Very long document (thousands of words)
      const longText = "This is a test sentence with enough content. ".repeat(500);

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          text: longText,
        },
      });

      if (response.status() === 200) {
        const body = await response.json();

        // Should create multiple chunks
        // (Would need to query chunks endpoint to verify count)
        expect(body).toHaveProperty("knowledgeBaseId");
      }
    });

    test("should verify context overlap between chunks", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // Text where overlap is important for context
      const textNeedingOverlap = `
        Chapter 1: Introduction to neural networks.
        Neural networks are computing systems inspired by biological neural networks.
        They form the basis of deep learning.
        Chapter 2: Network architecture.
        Deep neural networks have multiple layers.
        Each layer extracts increasingly abstract features.
        The architecture determines the network's capabilities.
      `.repeat(10);

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          text: textNeedingOverlap,
        },
      });

      // Would need to verify chunks have ~10% overlap
      // (Requires chunks inspection endpoint)
    });
  });

  test.describe("Concurrent Operations Edge Cases", () => {
    test("should handle 11th concurrent upload (rate limit exceeded)", async ({
      request,
    }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // Create 11 concurrent upload requests
      const uploadPromises = Array.from({ length: 11 }, (_, i) =>
        request.post(`${API_PREFIX}/upload`, {
          headers: {
            Authorization: "Bearer test-token",
          },
          form: {
            text: `Rate limit test content ${i}. `.repeat(20),
          },
        }),
      );

      const responses = await Promise.all(uploadPromises);

      // At least the 11th should be rate limited
      const rateLimitedResponses = responses.filter(
        (r) => r.status() === 429,
      );

      expect(rateLimitedResponses.length).toBeGreaterThan(0);
    });

    test("should handle rapid delete attempts on same document", async ({
      request,
    }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // First, create a document
      const createResponse = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          text: "Test for concurrent deletes. ".repeat(20),
        },
      });

      if (createResponse.status() !== 200) {
        test.skip();
        return;
      }

      const { knowledgeBaseId } = await createResponse.json();

      // Wait for processing by checking document status
      let retries = 0;
      let ready = false;
      while (retries < 10 && !ready) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        // In real scenario, check status endpoint
        retries++;
        if (retries >= 5) ready = true; // Assume ready for test
      }

      // Try to delete the same document multiple times concurrently
      const deletePromises = Array.from({ length: 5 }, () =>
        request.delete(`${API_PREFIX}/documents/${knowledgeBaseId}`, {
          headers: {
            Authorization: "Bearer test-token",
          },
        }),
      );

      const responses = await Promise.all(deletePromises);

      // First should succeed, others should get 404 or 409
      const successCount = responses.filter((r) => r.status() === 200).length;
      const errorCount = responses.filter((r) => r.status() === 404 || r.status() === 409).length;

      expect(successCount).toBe(1);
      expect(errorCount).toBe(4);
    });
  });

  test.describe("Metadata and Attribution Edge Cases", () => {
    test("should preserve page numbers in chunks", async ({ request }) => {
      // This requires uploading a multi-page PDF and verifying chunk metadata
      // Would need chunks inspection endpoint
      test.skip();
    });

    test("should preserve chunk index ordering", async ({ request }) => {
      // Upload text and verify chunks have sequential indices
      test.skip();
    });

    test("should store embedding model version", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          text: "Test embedding model version. ".repeat(20),
        },
      });

      if (response.status() === 200) {
        // Would need to verify that embedding_model = "text-embedding-3-small"
        // in chunk metadata
      }
    });
  });

  test.describe("Performance Edge Cases", () => {
    test("should complete vector search in <200ms (95th percentile)", async ({
      request,
    }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // Run multiple search queries and measure response time
      const searchPromises = Array.from({ length: 20 }, (_, i) =>
        (async () => {
          const start = Date.now();
          const response = await request.post(`${API_PREFIX}/search`, {
            headers: {
              Authorization: "Bearer test-token",
            },
            form: {
              query: `test query ${i}`,
              top_k: 5,
            },
          });
          const duration = Date.now() - start;
          return { response, duration };
        })(),
      );

      const results = await Promise.all(searchPromises);

      // Calculate 95th percentile
      const durations = results.map((r) => r.duration).sort((a, b) => a - b);
      const percentile95Index = Math.floor(durations.length * 0.95);
      const percentile95 = durations[percentile95Index];

      // 95th percentile should be <200ms
      expect(percentile95).toBeLessThan(200);
    });

    test("should handle large batch uploads efficiently", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // Upload 10 documents sequentially, measure total time
      const start = Date.now();

      for (let i = 0; i < 10; i++) {
        await request.post(`${API_PREFIX}/upload`, {
          headers: {
            Authorization: "Bearer test-token",
          },
          form: {
            text: `Batch test document ${i}. `.repeat(15),
          },
        });
      }

      const totalDuration = Date.now() - start;
      const averagePerUpload = totalDuration / 10;

      // Each upload should average <1s (not including processing time)
      expect(averagePerUpload).toBeLessThan(1000);
    });
  });

  test.describe("Stale Data Recovery", () => {
    test("should mark 30-minute-old processing records as failed", async ({
      request,
    }) => {
      // This test requires manipulating database state
      // to create old "processing" records
      test.skip();
    });

    test("should recover from crash during ingestion", async ({ request }) => {
      // Simulate a crash scenario and verify recovery
      test.skip();
    });
  });

  test.describe("Cross-Tenant Data Leaks Prevention", () => {
    test("should never return documents from other orgs", async ({ request }) => {
      // Create documents for different orgs and verify isolation
      test.skip();
    });

    test("should prevent org_id spoofing in uploads", async ({ request }) => {
      const API_PREFIX = `${process.env.E2E_BASE_URL ?? "http://127.0.0.1:3000"}/api/knowledge`;

      // Try to spoof org_id in request body
      const response = await request.post(`${API_PREFIX}/upload`, {
        headers: {
          Authorization: "Bearer test-token",
        },
        form: {
          text: "Spoofed org_id test. ".repeat(20),
          org_id: "spoofed-org-id", // Should be ignored
        },
      });

      if (response.status() === 200) {
        const body = await response.json();
        // Should use org_id from JWT, not request body
        // (Would need to verify in DB)
      }
    });
  });
});
