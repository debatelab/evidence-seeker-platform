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
  operationId?: string | null;
  errorMessage?: string | null;
  createdAt: string;
  startedAt?: string | null;
  completedAt?: string | null;
}
