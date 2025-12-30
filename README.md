# **Evidence Seeker Platform**

Evidence Seeker Platform empowers researchers, students, and debaters to build domain-specific AI fact-checkers without writing code. This project provides a user-friendly interface for the debatelab/evidence-seeker Python library, allowing non-technical users to set up, manage, and deploy domain-specific fact-checkers.

## **🎯 What is an EvidenceSeeker?**

An Evidence Seeker is an AI-based fact-checker that determines if a statement is supported or contradicted by a specific body of text (a corpus). It uses a sophisticated pipeline to analyze statements, retrieve relevant evidence, and assess the level of confirmation.

## **✨ Key Features**

* **Multiple AI Backends**: Supports various inference APIs and local models.  
* **Vector Search**: Uses state-of-the-art embeddings for semantic search.  
* **Flexible Configuration**: YAML-based setup for all pipeline components.
* **Evidence-Seeker Integration**: End-to-end fact-checking pipeline wired to the Evidence Seeker library.

## **🚀 Minimal Viable Product (MVP) Scope**

This is the full feature set for the initial release.

### **User & Access Control**

* **Authentication**: Users can register and log in.
* **Roles**: Users can have different roles with varying levels of access:
  * **PLATFORM_ADMIN**: Full administrative access to all Evidence Seekers and platform-wide user management (can delete users, manage all content).
  * **EVSE_ADMIN**: Full control over specific Evidence Seekers they create or are assigned to (can invite others, manage documents, configure settings).
  * **EVSE_READER**: Can view and test specific Evidence Seekers they have access to, even if private.

### **Evidence Seeker Management**

* **CRUD**: An EVSE_ADMIN can create, view, update, and delete an Evidence Seeker (including its logo, title, and description).  
* **Publishing**: An EVSE_ADMIN can publish/unpublish an Evidence Seeker to control public visibility.  
* **Testing**: Admins and readers can test any Evidence Seeker they have access to via a simple text input interface.

### **Document & Configuration**

* **Document Management**: An EVSE_ADMIN can upload (.pdf, .txt), manage metadata for (title, description), and delete documents for an Evidence Seeker.  
* **Embedding Generation**: Upon upload, document embeddings are automatically generated and stored.  
* **Simple Configuration**: A user-friendly interface for essential settings, like selecting an inference provider and entering API tokens (which must be stored encrypted).  
* **Language Defaults**: Each Evidence Seeker stores a primary language (e.g., DE or EN) that we forward to the preprocessing pipeline so outputs match the corpus language.  
* **Expert Configuration**: A text area for advanced YAML configuration is available for power users.

#### Simplified Configuration Flow

1. **Guided creation wizard** – Creating an Evidence Seeker now walks admins through three steps (basics, Hugging Face credentials, review) before the project is created so no seeker is left without working inference settings.
2. **Upload step expectations** – The guided uploader states that files can take a moment because embeddings are generated right after the upload lands, so admins know a slow upload is normal.
3. **Status-driven management** – Every seeker surfaces its configuration state via badges on the list page, within the management header, and on the configuration tab. Status metadata includes the current setup mode, last configured timestamp, and the requirements that are still missing.
4. **Workflow guards** – Document uploads, reindexing, semantic search, and fact-check runs are blocked in both the UI and API until the configuration state is `READY`. Users see a call-to-action to open the configuration tab, while the backend returns `409 Conflict` with machine-readable details so clients can respond gracefully.
5. **Expert mode toggle** – Advanced retrieval controls are hidden by default. Once the simple setup succeeds, admins can opt into expert mode per seeker to edit backend/language/override fields. They can revert to simple mode at any time to rely on platform defaults.
6. **API key rotation** – The configuration tab exposes the API Key Manager so admins can add a new Hugging Face key, switch the active credential, and remove the old key without downtime. Rotating a key automatically re-validates the configuration state.

### **Public Interface**

* **Discovery**: Non-registered users can view a list of all **public** Evidence Seekers.  
* **Interaction**: Non-registered users can test public Evidence Seekers and, if permitted, view and download their source documents.

### **Performance Considerations**

* **Document Limits**: Maximum 10MB per file, 100 documents per Evidence Seeker for MVP
* **Rate Limiting**: API calls throttled, especially for testing endpoints
* **Concurrent Users**: Managed queue for embedding generation to prevent overload

### **Security Specifics**

* **API Key Encryption**: Fernet symmetric encryption for storing user API keys
* **CORS Configuration**: Properly configured for frontend-backend communication
* **Input Sanitization**: All YAML configuration validated and sanitized

## **🛠️ Tech Stack**

This stack is chosen for rapid development, type safety, and operational simplicity.

| Component | Technology | Implementation Notes |
| :---- | :---- | :---- |
| **Backend** | **FastAPI** with **uv** | Fast, modern, and provides automatic type validation and API docs. |
| **ORM** | **SQLAlchemy 2.0** + **Alembic** | Modern async support, excellent pgvector integration, robust migration system |
| **Logging** | **Loguru** | Simple, powerful, and more developer-friendly than the standard library. |
| **Frontend** | **React** with **TypeScript** & **Tailwind CSS** | A robust and productive stack for building modern user interfaces. |
| **Database** | **PostgreSQL** + **pgvector** | pgvector allows storing embeddings directly in Postgres, avoiding the need for a separate vector database and simplifying the stack significantly. |
| **File Storage** | **Local Filesystem** | The FastAPI backend stores uploads on a dedicated volume configured via `UPLOAD_STORAGE_PATH` (defaults to `/app/uploads` inside containers). The file handling layer is abstracted so switching to S3/minio later remains simple. |
| **Auth & RBAC** | **fastapi-users Library** | A complete, battle-tested solution for user management, JWT authentication, and role-based access. **We will not build this from scratch.** We will extend fastapi-users for group-based permissions |
| **API Documentation** | **FastAPI built-in** + **Swagger UI** | Auto-generated, interactive API documentation |
| **Testing** | **pytest** + **Vitest** | Comprehensive testing for both backend and frontend |
| **Code Quality** | **Black, Ruff, mypy** (Python) + **ESLint, Prettier** (TypeScript) | Automated code formatting and quality checks |
| **Deployment** | **Docker Compose** | A multi-container setup: **1. Backend** (FastAPI), **2. Frontend** (Nginx), **3. Database** (Postgres), **4. Reverse Proxy** (Traefik/Nginx). This isolates services and mirrors production. |
| **Development** | **Hybrid Approach** | Run **Postgres in Docker** for stability. Run the **FastAPI backend and React frontend locally** for fast hot-reloading. |
| **Environment Management** | **.env files** | Secure configuration management with environment variables |

## **� Runtime Requirements (Node & npm)**

To avoid issues with optional native Rollup binaries (e.g. `@rollup/rollup-linux-x64-gnu` not resolving on CI), this repository standardizes on:

* **Node.js:** 24.0.2 or later
* **npm:** 11.3.0 or later (ships with the fix for optional dependency installation across platforms)

Enforcement aids:
* `.nvmrc` at the repo root (run `nvm use` after cloning)
* `engines` field in root and frontend `package.json`

### Clean Reinstall Steps (after updating Node/npm)

```bash
rm -rf node_modules frontend/node_modules package-lock.json
nvm install 24.0.2 # or use your version manager (Volta, asdf)
nvm use 24.0.2
npm install
```

If using a workspace-aware install, the root `package-lock.json` will include the frontend workspace resolution.


## **�📊 Data Model Overview**

Core relationships:
- **User** → **EvidenceSeeker** (many-to-many through permissions table)
- **EvidenceSeeker** → **Documents** (one-to-many)
- **Document** → **Embeddings** (one-to-many)
- **User** → **APIKeys** (one-to-many, encrypted storage)

## **🗺️ 5-Week Development Plan**

This iterative plan is designed to tackle risk early and deliver a functional product within the one-month timeframe. Each iteration represents a one-week sprint.

### **Iteration 1: Project Foundation & Core Auth (Week 1)**

**Goal**: A runnable project skeleton where a user can sign up and log in.

1. **Setup**: Initialize FastAPI and React repositories.  
2. **Database**: Set up SQLAlchemy models with proper relationships, configure Alembic for migrations
3. **Containerization**: Create the docker-compose.yml to run Postgres with health checks.  
4. **Authentication**: Integrate fastapi-users to handle user registration and JWT login.  
5. **UI**: Build the basic login and registration pages in React.  
6. **Early Deployment**: Deploy the skeleton to the target server to identify environmental issues immediately.
7. **CI/CD**: Basic CI pipeline with linting, type checking, and tests
8. **Logging**: Implement structured logging with correlation IDs using Loguru

### **Iteration 2: Evidence Seeker & Document Scaffolding (Week 2)**

**Goal**: Allow an authenticated user to create an Evidence Seeker and manage its associated documents *without* the AI pipeline.

1. **Database Models**: Define and create the database tables for EvidenceSeeker and Document.  
2. **API Endpoints**: Build the backend CRUD endpoints for managing Evidence Seekers with pagination.  
3. **File Handling**: Implement the file upload/delete logic for documents and logos with type validation.  
4. **UI Scaffolding**: Create the frontend views for creating, listing, and managing Evidence Seekers and their documents.
5. **Component Library**: Build reusable React components for common UI patterns
6. **File Validation**: Add file type validation and size limits

### **Iteration 3: AI Integration & User Roles (Week 3)**

**Goal**: Complete AI infrastructure and implement user collaboration features.

1. **Embedding Pipeline**: Hook into the document upload process. After a file is saved, trigger the evidence-seeker library to generate and store its embeddings in the pgvector column.
2. **Query Endpoint**: Create the core backend API endpoint that accepts a user's statement, passes it to the evidence-seeker pipeline for analysis, and returns the result.
3. **Configuration Management**: Implement the "Minimal Config Mode" for securely storing API keys and other essential settings.
4. **User Roles & Permissions**: Implement the role-based access control system with three roles:
   - **PLATFORM_ADMIN**: Full administrative access to all Evidence Seekers and platform-wide user management
   - **EVSE_ADMIN**: Full control over specific Evidence Seekers they create or are assigned to
   - **EVSE_READER**: Can view and test specific Evidence Seekers they have access to
5. **Role Management UI**: Build interface for admins to invite users and assign roles to Evidence Seekers.
6. **API Security**: Secure all relevant API endpoints, ensuring users can only access or modify the Evidence Seekers they have permission for.

### **Iteration 4: Testing Interface & Public View (Week 4)**

**Goal**: Make the created Evidence Seekers usable and publicly discoverable.

1. **Testing UI**: Build the React component that allows users to input a statement, call the query endpoint, and clearly display the analysis results.  
2. **Public/Private Logic**: Implement the "publish/unpublish" feature.  
3. **Public Pages**: Create the public-facing pages that list and display all *public* Evidence Seekers for non-registered users.
4. **Result Caching**: Implement caching for frequently tested statements
5. **Export Functionality**: Add ability to export test results
6. **Shareable Links**: Create shareable links for public Evidence Seekers

### **Iteration 5: Final Polish & Production Readiness (Week 5)**

**Goal**: Polish the user experience and prepare for MVP launch (now complete).

1. **UI/UX Polish**: Refine the user interface, add feedback messages (e.g., "Upload successful"), and conduct thorough testing.
2. **Documentation**: Clean up and finalize the README.md.
3. **Monitoring**: Add basic monitoring and health check dashboard
4. **Backup Strategy**: Implement backup procedures for uploads and database
5. **Admin Dashboard**: Create basic admin view for system health
6. **Performance Optimization**: Final performance tuning and caching improvements
7. **Production Configuration**: Environment setup and deployment preparation

## **⚠️ Error Handling & User Feedback**

- **Graceful Degradation**: If AI services are unavailable, queue requests for retry
- **User Notifications**: Toast notifications for all async operations
- **Error Boundaries**: React error boundaries to prevent full app crashes
- **Detailed Logging**: Structured logs with request IDs for debugging
- **User-Friendly Messages**: Clear, actionable error messages for users

## **✅ Critical Success Factors**

These features must work flawlessly for MVP success:

1. **Reliable Document Processing**: Embeddings must generate successfully
2. **Accurate Fact-Checking**: Results must be trustworthy and consistent
3. **Responsive UI**: Sub-second response for UI interactions
4. **Secure API Keys**: Zero exposure of user credentials
5. **Stable Deployment**: 99% uptime target for MVP

## **🔮 Post-MVP Roadmap**

- **Advanced Configuration**: YAML editor with syntax highlighting and validation
- **Social Media integration**: Integration as chatbot into Facebook, Twitter, Discord, ...
- **API Access**: Public API for programmatic access with API key management
- **Cloud Storage**: S3/MinIO integration for scalable file storage
- **Advanced Search**: Full-text search across evidence seekers/documents

## **🚦 Development Guidelines**

### **Code Quality Standards**
- **Python**: Black formatting, Ruff linting, mypy type checking
- **TypeScript**: ESLint + Prettier, strict TypeScript configuration
- **Testing**: Minimum 80% code coverage for critical paths
- **Documentation**: Docstrings for all public functions, JSDoc for TypeScript

### **Git Workflow**
- **Branching**: Feature branches from `develop`, merge to `main` for releases
- **Commits**: Conventional commits format for automatic changelog generation
- **Reviews**: All PRs require review before merging
- **CI/CD**: Automated testing on all PRs

### **Security Best Practices**
- **Dependencies**: Regular security audits with pip-audit and npm audit
- **Secrets**: Never commit secrets, use environment variables
- **Input Validation**: Validate all user inputs on both frontend and backend
- **Authentication**: JWT tokens with appropriate expiration times

## **📝 License**

[To be determined - consider MIT, Apache 2.0, or GPL depending on requirements]

## **👥 Contributors**

KIT DebateLab Team

## **🚀 Setup & Development Guide**

### **Prerequisites**
- Docker and Docker Compose
- Python 3.12+
- Node.js 18+
- Git

**Backend dependency note:** The backend now pulls `evidence-seeker` from PyPI at `0.1.4b0` (we previously pointed to the GitHub repo for testing).

### **Quick Start - Streamlined Development Environment**

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd evidence-seeker-platform
   ```

2. **Install dependencies for the root project**
   ```bash
   npm install
   ```

3. **Set up the complete development environment**
   ```bash
   # This single command sets up everything:
   # - Starts PostgreSQL in Docker
   # - Creates Python virtual environment with uv
   # - Installs all backend dependencies
   # - Runs database migrations
   # - Creates test user
   # - Installs frontend dependencies
   npm run setup
   ```

4. **Start development servers**
   ```bash
   # Start all services (database, backend, frontend) in parallel
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Database: localhost:5432

### **Alternative: Manual Setup**

If you prefer to set up components individually:

```bash
# Install all dependencies
npm run install:all

# Start database only
npm run db:up

# Setup backend only
npm run setup:backend

# Setup frontend only
npm run setup:frontend

# Start all development services
npm run dev
```

### **Test User Credentials**
A test user is automatically created for development:
- **Email**: `test@example.com`
- **Password**: `evidence123`

### **Environment Configuration**

For local development, use the provided `.env.dev` file in the backend directory:

```env
DATABASE_URL=postgresql://evidence_user:evidence_password@localhost:5432/evidence_seeker_dev
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
JWT_SECRET_KEY=dev-jwt-secret-key-change-in-production
LOG_LEVEL=DEBUG
```

For staging/production deployments, add the following variables to the backend `.env`
to automatically bootstrap the first platform admin when the service starts:

```env
INITIAL_ADMIN_EMAIL=admin@yourdomain.com
INITIAL_ADMIN_PASSWORD=CHANGE_THIS_STRONG_PASSWORD
INITIAL_ADMIN_USERNAME=admin
```

These values are read only on startup and are not stored in source control.

### **Database Setup**

1. **Initialize the database**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Create initial migration** (after model changes)
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

### **Development Workflow**

1. **Backend Development**
   ```bash
   cd backend
   # Run tests
   pytest -v

   # Run linting
   black .
   ruff check .
   mypy .

   # Run development server (auto-reload is for local dev only)
   uvicorn app.main:app --reload
   ```

2. **Frontend Development**
   ```bash
   cd frontend
   # Run development server
   npm run dev

   # Run tests
   npm run test

   # Run linting
   npm run lint
   ```

### **Docker Commands**

```bash
# Start all services (backend container becomes healthy after /health succeeds)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild and restart (uses production uvicorn command without --reload)
docker-compose up -d --build

# Run tests in containers
docker-compose exec backend pytest -v
docker-compose exec frontend npm run test
```

### **API Endpoints**

#### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/jwt/login` - User login
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/logout` - User logout

#### User Management
- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me` - Update current user
- `DELETE /api/v1/users/me` - Delete current user

### **Testing**

```bash
# Backend tests
cd backend
pytest -v --cov=app --cov-report=term-missing

# Frontend tests
cd frontend
npm run test

# Integration tests
docker-compose -f docker-compose.dev.yml up -d test_db
cd backend
pytest -v -m integration
```

#### Unified Postgres-only testing

All backend tests run against PostgreSQL (no SQLite fallback). This matches production and avoids driver/type mismatches (e.g., UUID, pgvector).

- Local default (if DATABASE_URL is not set):
   postgresql://evidence_user:evidence_password@localhost:5433/evidence_seeker_test
- Start the local test database:

```bash
docker-compose -f docker-compose.dev.yml --profile testing up -d test_db
```

- Or set a custom DATABASE_URL for tests before running pytest:

```bash
export DATABASE_URL=postgresql://user:pass@localhost:5432/your_test_db
cd backend
pytest -v
```

CI uses a Postgres service container; no external costs are incurred. Alembic is configured to read DATABASE_URL, and tests truncate tables per test to keep isolation.

#### One-command local tests

Fastest way (from repo root):

```bash
npm run test:backend
```

This will:
- Start the local `test_db` Postgres (on port 5433) if not already running
- Set `DATABASE_URL` automatically for the test run
- Run `pytest` in the backend with coverage

Alternative (backend-only helper script):

```bash
./backend/scripts/test-local.sh
```

Tip: The DB will stay up for reuse between runs. Stop it with:

```bash
docker-compose -f docker-compose.dev.yml --profile testing down -v
```

### **Deployment**

1. **Build and deploy**
   ```bash
   # Build Docker images
   docker-compose build

   # Deploy to production
   docker-compose -f docker-compose.yml up -d
   ```

2. **Environment variables for production**
   ```env
   DATABASE_URL=postgresql://evidence_user:evidence_password@db:5432/evidence_seeker
   SECRET_KEY=your-production-secret-key
   DEBUG=false
   CORS_ORIGINS=https://your-domain.com
   JWT_SECRET_KEY=your-production-jwt-secret
   LOG_LEVEL=WARNING
   ```

### **Troubleshooting**

**Common Issues:**
- **Port conflicts**: Make sure ports 3000, 8000, and 5432 are available
- **Database connection**: Check that PostgreSQL is running and accessible
- **Environment variables**: Ensure all required environment variables are set
- **Dependencies**: Run `npm install` in frontend directory if needed

**Debug Commands:**
```bash
# Check container status
docker-compose ps

# View backend logs
docker-compose logs backend

# View frontend logs
docker-compose logs frontend

# Access database
docker-compose exec db psql -U evidence_user -d evidence_seeker

# Restart specific service
docker-compose restart backend

# Check backend health status exposed to dependent services
docker-compose ps backend
```

### **Project Structure**

```
evidence-seeker-platform/
├── backend/                 # FastAPI backend
│   ├── app/                # Main application
│   │   ├── api/           # API routers
│   │   ├── core/          # Core configuration
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── main.py        # Application entry point
│   ├── tests/             # Test files
│   ├── pyproject.toml     # Python project config & dependencies (managed with uv)
│   ├── Dockerfile         # Backend container config
├── frontend/               # React frontend
│   ├── src/               # Source code
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks
│   │   ├── types/         # TypeScript types
│   │   ├── utils/         # Utility functions
│   │   └── App.tsx        # Main app component
│   ├── public/            # Static assets
│   ├── package.json       # Node.js dependencies
│   ├── Dockerfile         # Frontend container config
│   ├── vite.config.ts     # Vite configuration
│   └── tsconfig.json      # TypeScript configuration
├── docker-compose.yml      # Production setup
├── docker-compose.dev.yml  # Development setup
├── .github/workflows/     # CI/CD pipelines
└── README.md              # This file
```

---

**Iteration 1 - Implementation Complete!** ✅

*Status: All authentication features working*
- User registration and login ✅
- JWT token authentication ✅
- Protected API endpoints ✅
- React frontend with forms ✅
- Docker containerization ✅
- Testing infrastructure ✅
- CI/CD pipeline ✅

**Iteration 2 - Implementation Complete!** ✅

*Status: Evidence Seeker and document management working*
- Evidence Seeker CRUD operations ✅
- Document upload and management ✅
- File handling with validation ✅
- Frontend management interface ✅
- State-based upload flow ✅

**Iteration 3 - AI Integration & User Roles** ✅

*Status: AI infrastructure and user collaboration features complete*
- Vector database setup with pgvector ✅
- Embedding generation with LlamaIndex ✅
- Search interface and API endpoints ✅
- Configuration management ✅
- Progress tracking system ✅
- **User roles and permissions system** ✅
- **Evidence-seeker library integration** ✅

**Iteration 4 - Testing Interface & Public View** ✅

*Status: Testing and public access features complete*
- Testing UI for statement evaluation ✅
- Public/private publish controls ✅
- Public discovery pages ✅
- Result caching ✅
- Export functionality ✅
- Shareable links ✅

**Iteration 5 - Final Polish & Production Readiness** ✅

*Status: Production readiness and polish complete*
- UI/UX polish ✅
- Documentation finalized ✅
- Monitoring and health checks ✅
- Backup procedures ✅
- Admin dashboard ✅
- Performance optimization ✅
- Production configuration ✅

*Last Updated: December 2025*
