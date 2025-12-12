export type FactCheckRunStatus =
  | "PENDING"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLED";

export type FactCheckRunVisibility = "PUBLIC" | "UNLISTED" | "PRIVATE";

export interface FactCheckEvidence {
  id: number;
  libraryNodeId?: string | null;
  documentUuid?: string | null;
  documentId?: number | null;
  chunkLabel?: string | null;
  evidenceText: string;
  stance: string;
  score?: number | null;
  metadata?: Record<string, unknown> | null;
}

export interface FactCheckResult {
  id: number;
  interpretationIndex: number;
  interpretationText: string;
  interpretationType: string;
  confirmationLevel?: string | null;
  confidenceScore?: number | null;
  summary?: string | null;
  rawPayload?: Record<string, unknown> | null;
  evidence: FactCheckEvidence[];
}

export interface FactCheckRun {
  uuid: string;
  evidenceSeekerId: number;
  statement: string;
  status: FactCheckRunStatus;
  isPublic: boolean;
  visibility: FactCheckRunVisibility;
  createdAt: string;
  beganAt?: string | null;
  completedAt?: string | null;
  publishedAt?: string | null;
  featuredAt?: string | null;
  errorMessage?: string | null;
  operationId?: string | null;
}

export interface FactCheckRunDetail extends FactCheckRun {
  metrics?: Record<string, unknown> | null;
  configSnapshot?: Record<string, unknown> | null;
}

export interface CreateFactCheckRunRequest {
  statement: string;
  overrides?: Record<string, unknown>;
}

export interface RerunFactCheckRequest {
  overrides?: Record<string, unknown>;
}
