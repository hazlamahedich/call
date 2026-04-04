/**
 * Data factories for Knowledge Base testing.
 *
 * Uses faker for dynamic values to prevent collisions in parallel tests.
 * All factories accept overrides for explicit test intent.
 */

import { faker } from "@faker-js/faker";

/**
 * Knowledge Base entity types
 */
export type KnowledgeSourceType = "pdf" | "url" | "text";
export type KnowledgeStatus = "processing" | "ready" | "failed";

export interface KnowledgeBase {
  id: number;
  org_id: string;
  title: string;
  source_type: KnowledgeSourceType;
  source_url: string | null;
  file_path: string | null;
  file_storage_url: string | null;
  content_hash: string | null;
  chunk_count: number;
  status: KnowledgeStatus;
  error_message: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  soft_delete: boolean;
}

export interface KnowledgeChunk {
  id: number;
  org_id: string;
  knowledge_base_id: number;
  chunk_index: number;
  content: string;
  embedding: number[] | null;
  embedding_model: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  soft_delete: boolean;
}

/**
 * Create a Knowledge Base entity with sensible defaults
 */
export const createKnowledgeBase = (
  overrides: Partial<KnowledgeBase> = {},
): KnowledgeBase => ({
  id: faker.number.int({ min: 1, max: 100000 }),
  org_id: faker.string.uuid(),
  title: faker.lorem.sentence(3),
  source_type: "pdf",
  source_url: null,
  file_path: null,
  file_storage_url: null,
  content_hash: faker.string.hexadecimal({ length: 64 }),
  chunk_count: faker.number.int({ min: 1, max: 100 }),
  status: "ready",
  error_message: null,
  metadata: {
    page_count: faker.number.int({ min: 1, max: 50 }),
    word_count: faker.number.int({ min: 100, max: 10000 }),
  },
  created_at: faker.date.past().toISOString(),
  updated_at: faker.date.recent().toISOString(),
  soft_delete: false,
  ...overrides,
});

/**
 * Create a Knowledge Base with PDF source type
 */
export const createPDFKnowledgeBase = (
  overrides: Partial<KnowledgeBase> = {},
): KnowledgeBase =>
  createKnowledgeBase({
    source_type: "pdf",
    title: faker.system.fileName({ extension: "pdf" }),
    file_path: `uploads/${faker.string.uuid()}/document.pdf`,
    metadata: {
      page_count: faker.number.int({ min: 1, max: 50 }),
      word_count: faker.number.int({ min: 100, max: 10000 }),
    },
    ...overrides,
  });

/**
 * Create a Knowledge Base with URL source type
 */
export const createURLKnowledgeBase = (
  overrides: Partial<KnowledgeBase> = {},
): KnowledgeBase =>
  createKnowledgeBase({
    source_type: "url",
    source_url: faker.internet.url(),
    title: faker.company.name(),
    metadata: {
      source_url: faker.internet.url(),
      fetched_at: faker.date.recent().toISOString(),
    },
    ...overrides,
  });

/**
 * Create a Knowledge Base with text source type
 */
export const createTextKnowledgeBase = (
  overrides: Partial<KnowledgeBase> = {},
): KnowledgeBase =>
  createKnowledgeBase({
    source_type: "text",
    title: "Text Entry",
    metadata: {
      char_count: faker.number.int({ min: 100, max: 5000 }),
    },
    ...overrides,
  });

/**
 * Create a Knowledge Base in 'processing' status
 */
export const createProcessingKnowledgeBase = (
  overrides: Partial<KnowledgeBase> = {},
): KnowledgeBase =>
  createKnowledgeBase({
    status: "processing",
    chunk_count: 0,
    ...overrides,
  });

/**
 * Create a Knowledge Base in 'failed' status
 */
export const createFailedKnowledgeBase = (
  overrides: Partial<KnowledgeBase> = {},
): KnowledgeBase =>
  createKnowledgeBase({
    status: "failed",
    error_message: faker.helpers.arrayElement([
      "PDF is password-protected",
      "Failed to fetch URL: Connection timeout",
      "Unsupported file format",
      "PDF contains no extractable text",
    ]),
    ...overrides,
  });

/**
 * Create a Knowledge Chunk entity
 */
export const createKnowledgeChunk = (
  overrides: Partial<KnowledgeChunk> = {},
): KnowledgeChunk => ({
  id: faker.number.int({ min: 1, max: 100000 }),
  org_id: faker.string.uuid(),
  knowledge_base_id: faker.number.int({ min: 1, max: 100000 }),
  chunk_index: faker.number.int({ min: 0, max: 50 }),
  content: faker.lorem.paragraphs(3),
  embedding: faker.datatype.array({ min: 1536, max: 1536 }),
  embedding_model: "text-embedding-3-small",
  metadata: {
    page_number: faker.number.int({ min: 1, max: 50 }),
    section: faker.lorem.word(),
  },
  created_at: faker.date.past().toISOString(),
  soft_delete: false,
  ...overrides,
});

/**
 * Create a list of Knowledge Bases for pagination tests
 */
export const createKnowledgeBaseList = (
  count: number,
  overrides: Partial<KnowledgeBase> = {},
): KnowledgeBase[] =>
  Array.from({ length: count }, () => createKnowledgeBase(overrides));

/**
 * Create a Knowledge Base with duplicate content hash
 */
export const createDuplicateKnowledgeBase = (
  originalHash: string,
  overrides: Partial<KnowledgeBase> = {},
): KnowledgeBase =>
  createKnowledgeBase({
    content_hash: originalHash,
    title: faker.lorem.sentence(3),
    ...overrides,
  });

/**
 * Create test PDF file data
 */
export const createTestPDFFile = (
  size: number = 1024,
): { name: string; mimeType: string; buffer: Buffer } => ({
  name: faker.system.fileName({ extension: "pdf" }),
  mimeType: "application/pdf",
  buffer: Buffer.from(`%PDF-${faker.string.alphanumeric({ length: size })}`),
});

/**
 * Create oversized test file (>50MB)
 */
export const createOversizedFile = (): {
  name: string;
  mimeType: string;
  buffer: Buffer;
} => ({
  name: faker.system.fileName({ extension: "pdf" }),
  mimeType: "application/pdf",
  buffer: Buffer.alloc(51 * 1024 * 1024), // 51MB
});

/**
 * Create invalid file format
 */
export const createInvalidFile = (): {
  name: string;
  mimeType: string;
  buffer: Buffer;
} => ({
  name: faker.system.fileName({ extension: "exe" }),
  mimeType: "application/x-msdownload",
  buffer: Buffer.from("MZ\x90\x00"),
});
