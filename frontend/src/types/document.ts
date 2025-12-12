export interface Document {
  id: number;
  uuid: string; // External API identifier
  title: string;
  description: string | null;
  sourceUrl?: string | null;
  filePath: string;
  originalFilename: string; // Original filename with extension
  fileSize: number;
  mimeType: string;
  evidenceSeekerUuid: string; // External API uses UUID
  evidenceSeekerId?: number; // Keep for internal use
  indexFileKey?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface DocumentCreate {
  title: string;
  description?: string | null;
  sourceUrl?: string | null;
  file: File;
}

export interface FileUpload {
  file: File;
  title: string;
  description: string;
}

export interface DocumentIngestionResponse {
  document: Document;
  jobUuid: string;
  operationId: string | null;
}

export interface DocumentUpdate {
  title?: string;
  description?: string | null;
  sourceUrl?: string | null;
}
