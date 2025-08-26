# Implementation Plan

## [Overview]
Implement Evidence Seeker CRUD operations and document management scaffolding for Iteration 2.

This iteration focuses on building the core data models and API endpoints for Evidence Seekers and Documents without AI pipeline integration. The goal is to establish the foundation for managing fact-checking tools, including user permissions, file uploads, and basic CRUD operations. This will enable users to create Evidence Seekers, upload documents, and manage their collections through a complete web interface.

## [Types]
Define TypeScript interfaces and Python schemas for Evidence Seeker and Document entities with validation rules.

### Backend Schemas (Pydantic)
- **EvidenceSeekerCreate**: title (str, 1-100 chars), description (str, 0-500 chars), is_public (bool, default False)
- **EvidenceSeekerRead**: id (int), title (str), description (str), logo_url (Optional[str]), is_public (bool), created_by (int), created_at (datetime), updated_at (datetime)
- **EvidenceSeekerUpdate**: title (Optional[str]), description (Optional[str]), is_public (Optional[bool])
- **DocumentCreate**: title (str, 1-200 chars), description (str, 0-500 chars), file (UploadFile, PDF/TXT, max 10MB)
- **DocumentRead**: id (int), title (str), description (str), file_path (str), file_size (int), mime_type (str), evidence_seeker_id (int), created_at (datetime), updated_at (datetime)
- **PermissionCreate**: user_id (int), evidence_seeker_id (int), role (Enum: evse_admin, evse_reader)
- **PermissionRead**: id (int), user_id (int), evidence_seeker_id (int), role (str), created_at (datetime)

### Frontend Types (TypeScript)
- **EvidenceSeeker**: id (number), title (string), description (string), logoUrl (string | null), isPublic (boolean), createdBy (number), createdAt (string), updatedAt (string)
- **Document**: id (number), title (string), description (string), filePath (string), fileSize (number), mimeType (string), evidenceSeekerId (number), createdAt (string), updatedAt (string)
- **Permission**: id (number), userId (number), evidenceSeekerId (number), role ('evse_admin' | 'evse_reader'), createdAt (string)
- **FileUpload**: file (File), title (string), description (string)

## [Files]
Create new models, schemas, API routes, and frontend components while modifying existing files for integration.

### New Files
- `backend/app/models/evidence_seeker.py` - SQLAlchemy model for EvidenceSeeker entity
- `backend/app/models/document.py` - SQLAlchemy model for Document entity
- `backend/app/models/permission.py` - SQLAlchemy model for user permissions
- `backend/app/schemas/evidence_seeker.py` - Pydantic schemas for EvidenceSeeker API
- `backend/app/schemas/document.py` - Pydantic schemas for Document API
- `backend/app/api/evidence_seekers.py` - CRUD API endpoints for Evidence Seekers
- `backend/app/api/documents.py` - File upload and management endpoints
- `backend/app/core/file_utils.py` - File validation and storage utilities
- `frontend/src/types/evidenceSeeker.ts` - TypeScript interfaces
- `frontend/src/types/document.ts` - TypeScript interfaces for documents
- `frontend/src/components/EvidenceSeeker/EvidenceSeekerList.tsx` - List view component
- `frontend/src/components/EvidenceSeeker/EvidenceSeekerForm.tsx` - Create/edit form
- `frontend/src/components/Document/DocumentUpload.tsx` - File upload component
- `frontend/src/components/Document/DocumentList.tsx` - Document management
- `frontend/src/hooks/useEvidenceSeeker.ts` - Custom hook for API calls
- `frontend/src/hooks/useDocument.ts` - Custom hook for document operations

### Modified Files
- `backend/app/core/database.py` - Add new models to Base.metadata
- `backend/app/main.py` - Include new API routers
- `backend/app/core/config.py` - Add file upload settings (UPLOAD_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS)
- `frontend/src/App.tsx` - Add navigation and routing for Evidence Seeker pages
- `frontend/src/utils/api.ts` - Add API functions for new endpoints
- `backend/alembic/env.py` - Ensure new models are included in migrations

### Configuration Updates
- `docker-compose.yml` - Add volume mount for uploads directory
- `.env.dev` - Add UPLOAD_DIR, MAX_FILE_SIZE, ALLOWED_EXTENSIONS variables

## [Functions]
Create new API endpoints and utility functions for Evidence Seeker and document management.

### New Functions
- `create_evidence_seeker(db: Session, seeker: EvidenceSeekerCreate, user_id: int)` - backend/app/api/evidence_seekers.py
- `get_evidence_seekers(db: Session, user_id: int, skip: int = 0, limit: int = 100)` - backend/app/api/evidence_seekers.py
- `get_evidence_seeker(db: Session, seeker_id: int, user_id: int)` - backend/app/api/evidence_seekers.py
- `update_evidence_seeker(db: Session, seeker_id: int, seeker_update: EvidenceSeekerUpdate, user_id: int)` - backend/app/api/evidence_seekers.py
- `delete_evidence_seeker(db: Session, seeker_id: int, user_id: int)` - backend/app/api/evidence_seekers.py
- `upload_document(db: Session, file: UploadFile, title: str, description: str, evidence_seeker_id: int, user_id: int)` - backend/app/api/documents.py
- `get_documents(db: Session, evidence_seeker_id: int, user_id: int)` - backend/app/api/documents.py
- `delete_document(db: Session, document_id: int, user_id: int)` - backend/app/api/documents.py
- `validate_file(file: UploadFile) -> bool` - backend/app/core/file_utils.py
- `save_upload_file(file: UploadFile, destination: str) -> str` - backend/app/core/file_utils.py
- `delete_file(file_path: str)` - backend/app/core/file_utils.py

## [Classes]
Define new SQLAlchemy models for Evidence Seekers, Documents, and Permissions.

### New Classes
- **EvidenceSeeker** (backend/app/models/evidence_seeker.py)
  - Inherits from Base
  - Fields: id, title, description, logo_url, is_public, created_by, created_at, updated_at
  - Relationships: documents (one-to-many), permissions (one-to-many)

- **Document** (backend/app/models/document.py)
  - Inherits from Base
  - Fields: id, title, description, file_path, file_size, mime_type, evidence_seeker_id, created_at, updated_at
  - Relationships: evidence_seeker (many-to-one)

- **Permission** (backend/app/models/permission.py)
  - Inherits from Base
  - Fields: id, user_id, evidence_seeker_id, role, created_at
  - Relationships: user (many-to-one), evidence_seeker (many-to-one)
  - Unique constraint: (user_id, evidence_seeker_id)

## [Dependencies]
Add required packages for file handling and additional validation.

### Python Dependencies
- `python-multipart` (already in requirements.txt for file uploads)
- `aiofiles` (for async file operations)
- `pathlib` (standard library, for path handling)

### Frontend Dependencies
- `@types/file-saver` (TypeScript definitions for file handling)
- `react-dropzone` (for drag-and-drop file uploads)

## [Testing]
Create comprehensive tests for new models, API endpoints, and frontend components.

### Backend Tests
- `backend/tests/test_evidence_seekers.py` - CRUD operations, permissions, validation
- `backend/tests/test_documents.py` - File upload, validation, deletion
- `backend/tests/test_permissions.py` - Role-based access control
- `backend/tests/test_file_utils.py` - File validation and storage

### Frontend Tests
- `frontend/src/__tests__/components/EvidenceSeeker/EvidenceSeekerList.test.tsx`
- `frontend/src/__tests__/components/Document/DocumentUpload.test.tsx`
- `frontend/src/__tests__/hooks/useEvidenceSeeker.test.tsx`

## [Current Implementation Status]
Based on current codebase analysis:

### Completed:
- [x] Create SQLAlchemy models (EvidenceSeeker, Document, Permission) - All models exist and match specifications
- [x] Implement file utility functions - backend/app/core/file_utils.py exists
- [x] Create Pydantic schemas for API validation - All schemas (EvidenceSeeker, Document, Permission) created and implemented
- [x] Create Evidence Seeker CRUD API endpoints - backend/app/api/evidence_seekers.py implemented with full CRUD operations
- [x] Create Document upload and management API endpoints - backend/app/api/documents.py implemented with upload and management functions
- [x] Run database migrations and test backend APIs - Models and alembic setup complete, migration created and applied successfully
- [x] Create TypeScript interfaces and API hooks - frontend/src/types/evidenceSeeker.ts and document.ts implemented, hooks implemented
- [x] Build Evidence Seeker list and form components - EvidenceSeekerForm.tsx and EvidenceSeekerList.tsx fully implemented
- [x] Build Document upload and management components - DocumentUpload.tsx and DocumentList.tsx fully implemented with advanced features
- [x] Update main App component with routing and navigation - Evidence Seeker routes and navigation fully integrated in frontend/src/App.tsx
- [x] Update frontend/src/utils/api.ts - Base API client configured, Evidence Seeker APIs handled via custom hooks

### Partially Completed:
- [ ] Test complete user workflows end-to-end - Backend APIs tested, frontend integration needs verification

### Not Yet Implemented:
- [ ] Add comprehensive tests for all components - All new tests missing

### Modified Files Status:
- [x] backend/app/core/database.py - Exists, new models included via __init__.py imports
- [x] backend/app/main.py - Exists, new API routers added and configured
- [x] backend/app/core/config.py - Exists, file upload settings verified
- [x] frontend/src/App.tsx - Exists, Evidence Seeker routes added and fully configured
- [x] frontend/src/utils/api.ts - Exists, API functions configured and working
- [x] backend/alembic/env.py - Exists, configured for new models

## [Implementation Order]
Sequential implementation to minimize dependencies and enable testing at each stage.

1. [x] Create SQLAlchemy models (EvidenceSeeker, Document, Permission)
2. [ ] Create Pydantic schemas for API validation (EvidenceSeeker and Permission schemas)
3. [x] Implement file utility functions
4. [ ] Create Evidence Seeker CRUD API endpoints
5. [ ] Create Document upload and management API endpoints
6. [ ] Run database migrations and test backend APIs
7. [ ] Create TypeScript interfaces and API hooks
8. [ ] Build Evidence Seeker list and form components
9. [ ] Build Document upload and management components
10. [ ] Update main App component with routing and navigation
11. [ ] Add comprehensive tests for all components
12. [ ] Test complete user workflows end-to-end
