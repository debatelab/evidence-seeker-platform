export interface Document {
  id: number;
  uuid: string; // External API identifier
  title: string;
  description: string;
  filePath: string;
  fileSize: number;
  mimeType: string;
  evidenceSeekerUuid: string; // External API uses UUID
  evidenceSeekerId?: number; // Keep for internal use
  createdAt: string;
  updatedAt: string;
}

export interface DocumentCreate {
  title: string;
  description: string;
  file: File;
}

export interface FileUpload {
  file: File;
  title: string;
  description: string;
}
