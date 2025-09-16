/**
 * TypeScript types for embedding operations
 */

export interface EmbeddingStatus {
  document_id: number;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  embedding_count: number;
  model?: string;
  dimensions?: number;
  generated_at?: string;
}

export interface EmbeddingRegenerateRequest {
  document_id: number;
}

export interface EmbeddingModelInfo {
  model_name: string;
  dimensions: number;
  chunk_size: number;
  chunk_overlap: number;
  embed_batch_size: number;
}

export interface BatchEmbeddingStatus {
  document_id: number;
  status: string;
  embedding_count: number;
  model?: string;
  dimensions?: number;
  generated_at?: string;
  error?: string;
}

export interface BatchEmbeddingRequest {
  document_ids: number[];
}

export interface BatchEmbeddingResponse {
  results: BatchEmbeddingStatus[];
}
