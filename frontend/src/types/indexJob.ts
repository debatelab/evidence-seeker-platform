export type IndexJobStatus =
  | "QUEUED"
  | "RUNNING"
  | "SUCCEEDED"
  | "FAILED"
  | "CANCELLED";

export interface IndexJob {
  uuid: string;
  evidenceSeekerId: number;
  submittedBy: number;
  jobType: string;
  status: IndexJobStatus;
  documentUuid?: string | null;
  documentUuids?: string[] | null;
  payload?: Record<string, unknown> | null;
  operationId?: string | null;
  errorMessage?: string | null;
  createdAt: string;
  startedAt?: string | null;
  completedAt?: string | null;
}
