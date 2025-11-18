/**
 * TypeScript types for configuration management
 */

export interface APIKeyBase {
  provider: string;
  name: string;
  description?: string;
}

export interface APIKeyCreate extends APIKeyBase {
  api_key: string;
  expires_in_days?: number;
}

export interface APIKeyUpdate {
  name?: string;
  description?: string;
  is_active?: boolean;
}

export interface APIKeyRead extends APIKeyBase {
  id: number;
  evidence_seeker_id: number;
  evidence_seeker_uuid: string;
  is_active: boolean;
  last_used_at?: string;
  expires_at?: string;
  created_at: string;
  updated_at: string;
}

export interface APIKeyReadWithHash extends APIKeyRead {
  key_hash: string;
}

export interface APIKeyValidation {
  provider: string;
  api_key: string;
}

export interface APIKeyValidationResponse {
  is_valid: boolean;
  provider: string;
  message: string;
}

export interface AIConfig {
  embedding_model: string;
  embedding_dimensions: number;
  chunk_size: number;
  chunk_overlap: number;
  max_concurrent_embeddings: number;
  supported_providers: string[];
  default_similarity_threshold: number;
  max_search_results: number;
}

export interface SystemStats {
  total_documents: number;
  documents_with_embeddings: number;
  total_embeddings: number;
  total_api_keys: number;
  embedding_coverage: number;
}

export interface SupportedProviders {
  supported_providers: string[];
  embedding_model: string;
  vector_dimensions: number;
}

export interface DecryptedAPIKeyResponse {
  api_key_id: number;
  decrypted_key: string;
  warning: string;
}
