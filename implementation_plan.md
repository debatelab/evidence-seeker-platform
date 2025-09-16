# Implementation Plan

Integrate AI boilerplate functionality into the Evidence Seeker Platform, including embedding generation, vector search capabilities, and configuration management to prepare for the evidence-seeker library integration.

This implementation focuses on building the foundational AI infrastructure that will support the evidence-seeker pipeline, ensuring scalability for multiple concurrent users while maintaining security and performance standards.

[Types]
Define new data structures for embeddings, vector search, and configuration management.

**Embedding Types:**
- `EmbeddingVector`: Array of float32 values representing document embeddings (768 dimensions for paraphrase-multilingual-mpnet-base-v2)
- `EmbeddingMetadata`: Contains embedding generation timestamp, model used, and processing status
- `VectorSearchResult`: Contains document matches with similarity scores and metadata

**Configuration Types:**
- `APIKeyConfig`: Encrypted storage for API keys with provider-specific validation
- `EmbeddingConfig`: Model selection, dimensions, and processing parameters
- `PipelineConfig`: Evidence seeker pipeline settings and thresholds

**Search Types:**
- `SearchQuery`: User's statement with optional filters and search parameters
- `SearchResult`: Analysis result with confidence scores and supporting evidence
- `ProgressUpdate`: Real-time progress tracking for long-running operations

[Files]
Create new files and modify existing ones to support AI functionality.

**New Files:**
- `backend/app/models/embedding.py`: SQLAlchemy model for storing document embeddings with pgvector
- `backend/app/models/api_key.py`: Model for encrypted API key storage
- `backend/app/schemas/embedding.py`: Pydantic schemas for embedding operations
- `backend/app/schemas/api_key.py`: Schemas for API key management
- `backend/app/schemas/search.py`: Schemas for vector search and analysis
- `backend/app/core/embedding_service.py`: Service for generating and managing embeddings using LlamaIndex
- `backend/app/core/vector_search.py`: Vector search implementation using PGVectorStore
- `backend/app/core/config_service.py`: Configuration management with encryption
- `backend/app/api/embeddings.py`: API endpoints for embedding operations
- `backend/app/api/search.py`: API endpoints for vector search and analysis
- `backend/app/api/config.py`: API endpoints for configuration management
- `frontend/src/types/embedding.ts`: TypeScript types for embeddings
- `frontend/src/types/search.ts`: Types for search operations
- `frontend/src/types/config.ts`: Types for configuration management
- `frontend/src/hooks/useEmbedding.ts`: React hooks for embedding operations
- `frontend/src/hooks/useSearch.ts`: Hooks for search functionality
- `frontend/src/hooks/useConfig.ts`: Hooks for configuration management
- `frontend/src/components/Search/SearchInterface.tsx`: Main search UI component
- `frontend/src/components/Search/SearchResults.tsx`: Results display component
- `frontend/src/components/Config/ConfigForm.tsx`: Configuration management UI
- `frontend/src/components/Config/APIKeyManager.tsx`: API key management interface
- `frontend/src/components/Progress/ProgressIndicator.tsx`: Real-time progress updates

**Modified Files:**
- `backend/app/models/document.py`: Add embedding relationship and status fields
- `backend/app/api/documents.py`: Integrate embedding generation on upload using LlamaIndex workflow
- `backend/app/core/config.py`: Add AI-related configuration settings including embedding model
- `backend/requirements.txt`: Add LlamaIndex, pgvector, and embedding dependencies
- `backend/app/main.py`: Include new API routers for embeddings, search, and config
- `frontend/src/types/document.ts`: Add embedding-related fields
- `frontend/src/components/Document/DocumentUpload.tsx`: Add progress tracking for embedding generation
- `frontend/src/App.tsx`: Add new routes for search and configuration

[Functions]
Implement core functions for AI operations and configuration management.

**New Functions:**
- `generate_embeddings(document_id, config)`: Generate embeddings using HuggingFaceEmbedding with paraphrase-multilingual-mpnet-base-v2
- `store_embeddings(document_id, vectors, metadata)`: Store 768-dimensional embeddings in pgvector table
- `vector_search(query_embedding, filters, limit)`: Perform vector similarity search using PGVectorStore
- `analyze_statement(statement, context_docs)`: Analyze user statements (fake implementation initially)
- `encrypt_api_key(api_key, user_id)`: Encrypt and store API keys using Fernet
- `decrypt_api_key(encrypted_key)`: Decrypt API keys for use with embedding models
- `validate_config(config)`: Validate configuration settings including model compatibility
- `update_progress(operation_id, progress, status)`: Update operation progress for real-time UI updates

**Modified Functions:**
- `upload_document()`: Enhanced to trigger LlamaIndex document processing and embedding generation
- `save_upload_file()`: Updated to handle embedding processing workflow
- `get_documents()`: Include embedding status and generation progress in response

[Classes]
Define new classes for AI services and configuration management.

**New Classes:**
- `EmbeddingService`: Handles embedding generation using LlamaIndex and HuggingFaceEmbedding
- `VectorSearchService`: Manages vector search operations with PGVectorStore
- `ConfigService`: Manages encrypted configuration storage with Fernet encryption
- `ProgressTracker`: Tracks long-running operation progress with WebSocket support
- `APIKeyManager`: Handles API key encryption/decryption for secure storage
- `SearchAnalyzer`: Processes search queries and returns results with confidence scores

**Modified Classes:**
- `Document`: Add embedding-related fields and relationships
- `EvidenceSeeker`: Add configuration relationship for API keys and settings

[Dependencies]
Add required dependencies for AI functionality and security based on pgvector tutorial.

**New Packages:**
- `llama-index-vector-stores-postgres`: For PostgreSQL vector store integration
- `llama-index-embeddings-huggingface`: For HuggingFace embedding model support
- `sentence-transformers>=2.0.0`: Required for paraphrase-multilingual-mpnet-base-v2 model
- `pgvector==0.2.4`: PostgreSQL vector extension support (already present)
- `cryptography==41.0.7`: For API key encryption (already present)
- `websockets==12.0`: Real-time progress updates
- `asyncio`: For concurrent processing (standard library)

**Version Updates:**
- `sqlalchemy==2.0.23`: Ensure pgvector compatibility (already present)
- `pydantic==2.5.0`: Latest version for better validation (already present)

[Testing]
Comprehensive testing strategy for AI functionality.

**Unit Tests:**
- `test_embedding_service.py`: Test embedding generation with paraphrase-multilingual-mpnet-base-v2
- `test_vector_search.py`: Test search functionality and accuracy with pgvector
- `test_config_service.py`: Test configuration encryption/decryption
- `test_progress_tracking.py`: Test progress update mechanisms

**Integration Tests:**
- `test_document_upload_with_embeddings.py`: End-to-end upload flow with LlamaIndex processing
- `test_search_pipeline.py`: Complete search and analysis flow
- `test_concurrent_uploads.py`: Multi-user upload scenarios with embedding generation

**Frontend Tests:**
- `SearchInterface.test.tsx`: Search UI component tests
- `ConfigForm.test.tsx`: Configuration form tests
- `ProgressIndicator.test.tsx`: Progress tracking tests

[Implementation Order]
Sequential implementation following the pgvector tutorial workflow.

1. **Database Setup**: Ensure pgvector extension and create vector tables
2. **Core Dependencies**: Install LlamaIndex, HuggingFace embeddings, sentence-transformers
3. **Embedding Service**: Implement EmbeddingService with HuggingFaceEmbedding configuration
4. **Vector Store**: Set up PGVectorStore with 768 dimensions for the model
5. **Document Integration**: Modify upload process to use LlamaIndex SimpleDirectoryReader
6. **API Endpoints**: Create embedding and search API endpoints
7. **Configuration Management**: Implement encrypted API key storage
8. **Progress Tracking**: Add real-time progress updates for embedding generation
9. **Frontend Components**: Build search interface and configuration UI
10. **Testing**: Comprehensive testing of all AI components
11. **Performance Optimization**: Add caching and concurrent processing
12. **Documentation**: Update API documentation with embedding specifications
