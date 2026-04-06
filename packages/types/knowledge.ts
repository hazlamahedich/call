export interface NamespaceViolation {
  code: "NAMESPACE_VIOLATION";
  message: string;
  timestamp: string;
}

export interface KnowledgeSearchResult {
  id: number;
  knowledgeBaseId: number;
  content: string;
  similarity: number;
  metadata: Record<string, unknown>;
}

export interface KnowledgeSearchResponse {
  results: KnowledgeSearchResult[];
  query: string;
  totalResults: number;
  guardOverheadMs: number;
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
