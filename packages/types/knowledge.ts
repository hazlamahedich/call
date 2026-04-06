export interface NamespaceViolation {
  code: "NAMESPACE_VIOLATION";
  message: string;
  timestamp: string;
}

export interface KnowledgeSearchResult {
  chunkId: number;
  knowledgeBaseId: number;
  content: string;
  similarity: number;
  metadata: Record<string, unknown>;
}

export interface KnowledgeSearchResponse {
  results: KnowledgeSearchResult[];
  query: string;
  total: number;
}

export interface IsolationAuditCheck {
  checkType: string;
  orgA: string;
  orgB: string;
  passed: boolean;
  details: string;
}

export interface IsolationAuditReport {
  timestamp: string;
  totalChecks: number;
  passed: number;
  failed: number;
  details: IsolationAuditCheck[];
  tenantCount: number;
  pairsChecked: number;
  pairsSkipped: number;
}
