export interface EvidenceSearchRequest {
  query: string;
  topK?: number;
  metadataFilters?: Record<string, unknown>;
  documentUuids?: string[];
}

export interface EvidenceSearchHit {
  score: number;
  text: string;
  documentUuid?: string | null;
  documentId?: number | null;
  metadata?: Record<string, unknown> | null;
}

export interface EvidenceSearchResponse {
  query: string;
  results: EvidenceSearchHit[];
}

export interface SystemStatistics {
  totalDocuments: number;
  indexedDocuments: number;
  evidenceSeekerSettings: number;
  factCheckRuns: number;
  activeIndexJobs: number;
  totalApiKeys: number;
}

export interface ProgressUpdate {
  operation_id: string;
  progress: number;
  status: string;
  message: string;
  current_step?: number | null;
  total_steps?: number | null;
  estimated_time_remaining?: number | null;
  timestamp?: string;
  metadata?: Record<string, unknown>;
}
