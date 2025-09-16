/**
 * TypeScript types for search operations
 */

export interface SearchQuery {
  query: string;
  limit?: number;
  similarity_threshold?: number;
  document_ids?: number[];
}

export interface SearchResult {
  embedding_id: number;
  document_id: number;
  chunk_text: string;
  chunk_index: number;
  model_name: string;
  similarity_score: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
}

export interface EmbeddingSearchQuery {
  embedding: number[];
  limit?: number;
  similarity_threshold?: number;
  document_ids?: number[];
}

export interface EmbeddingSearchResponse {
  query_embedding_dimensions: number;
  results: SearchResult[];
  total_results: number;
}

export interface DocumentChunk {
  id: number;
  chunk_index: number;
  chunk_text: string;
  total_chunks: number;
  processing_time_ms?: number;
  created_at: string;
}

export interface DocumentChunksResponse {
  document_id: number;
  chunks: DocumentChunk[];
}

export interface SearchStatistics {
  total_embeddings: number;
  documents_with_embeddings: number;
  embedding_models: Array<{
    model: string;
    count: number;
  }>;
  vector_dimensions: number;
}

export interface SimilarDocumentsQuery {
  limit?: number;
}

export interface SimilarDocumentsResponse {
  document_id: number;
  query_chunk: string;
  similar_documents: SearchResult[];
}

export interface AnalysisQuery {
  statement: string;
  context_document_ids?: number[];
  max_context_chunks?: number;
}

export interface AnalysisResult {
  statement: string;
  analysis: string;
  confidence_score: number;
  supporting_evidence: SearchResult[];
  context_used: number;
}

export interface ProgressUpdate {
  operation_id: string;
  progress: number;
  status: string;
  message: string;
  current_step?: number;
  total_steps?: number;
  estimated_time_remaining?: number;
  timestamp: string;
  metadata: Record<string, any>;
}

export interface BatchOperationStatus {
  operation_id: string;
  total_items: number;
  processed_items: number;
  successful_items: number;
  failed_items: number;
  status: string;
  created_at: string;
  updated_at: string;
}
