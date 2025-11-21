import type { FactCheckResult, FactCheckRun, FactCheckRunDetail } from "./factCheck";

export interface PublicEvidenceSeekerSummary {
  uuid: string;
  title: string;
  description: string | null;
  language: string | null;
  logoUrl: string | null;
  publishedAt: string | null;
  documentCount: number;
  latestFactCheckAt: string | null;
}

export interface PublicEvidenceSeekerDetailSummary
  extends PublicEvidenceSeekerSummary {
  createdAt: string;
  updatedAt: string;
  isPublic: boolean;
}

export interface PublicDocument {
  uuid: string;
  title: string;
  description: string | null;
  originalFilename: string;
  createdAt: string;
  updatedAt: string;
}

export interface PaginatedPublicEvidenceSeekers {
  items: PublicEvidenceSeekerSummary[];
  total: number;
  page: number;
  pageSize: number;
}

export interface PublicEvidenceSeekerDetailResponse {
  seeker: PublicEvidenceSeekerDetailSummary;
  documents: PublicDocument[];
  recentFactChecks: PublicFactCheckRunSummary[];
}

export interface PublicFactCheckRunSummary {
  uuid: string;
  statement: string;
  status: FactCheckRun["status"];
  completedAt: string | null;
  publishedAt: string | null;
  evidenceSeekerUuid: string;
  evidenceSeekerId: number;
  evidenceSeekerTitle: string;
}

export interface PublicFactCheckRunsResponse {
  items: PublicFactCheckRunSummary[];
  total: number;
  page: number;
  pageSize: number;
}

export interface PublicFactCheckRunDetailResponse {
  run: FactCheckRunDetail;
  seeker: PublicEvidenceSeekerSummary;
  results: FactCheckResult[];
}
