# Evidence Seeker Platform

Evidence Seeker Platform is a full-stack application for creating, configuring, and operating domain-specific AI fact-checkers built on top of the Evidence Seeker library. It combines a FastAPI backend, a React frontend, and PostgreSQL with pgvector.

For the detailed product scope, roadmap, and AI-oriented working spec, see [`PROJECT_SPEC.md`](./PROJECT_SPEC.md).

## Overview

- `backend/`: FastAPI application, database models, migrations, and tests
- `frontend/`: React + Vite application
- `docker-compose.dev.yml`: local development database and test database
- `docker-compose.yml`: source-based multi-service stack
- `docker-compose.prod.yml.example`: image-based production deployment template

## Requirements

- Docker and Docker Compose
- Python 3.12+
- Node.js 24.0.2 or later
- npm 11.3.0 or later

The repository standardizes on Node 24.0.2+ and npm 11.3.0+ to avoid optional Rollup binary issues across environments.

## Quick Start

```bash
npm install
npm run setup
npm run dev
```

`npm run setup` starts PostgreSQL, creates the backend virtual environment, installs dependencies, runs migrations, resets local uploads, and seeds a test user for development.

After startup:

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>
- PostgreSQL: `localhost:5432`

Development test user:

- Email: `test@example.com`
- Password: `evidence123`

## Useful Commands

```bash
npm run test
npm run test:backend
npm run lint
npm run db:up
npm run db:down
```

If you want to run services individually:

```bash
npm run dev:backend
npm run dev:frontend
npm run dev:db
```

## Configuration

- Shared root environment template: [`.env.example`](./.env.example)
- Local backend development env: [`backend/.env.dev`](./backend/.env.dev)
- Production backend env template: [`backend/.env.prod.example`](./backend/.env.prod.example)

`npm run setup:backend` copies `backend/.env.dev` to `backend/.env` for local development.

For staging or production, you can bootstrap the first platform admin on startup with:

```env
INITIAL_ADMIN_EMAIL=admin@yourdomain.com
INITIAL_ADMIN_PASSWORD=CHANGE_THIS_STRONG_PASSWORD
INITIAL_ADMIN_USERNAME=admin
```

## Deployment

For the full server deployment guide, SSL setup, backup strategy, and operations notes, see [`deployment.md`](./deployment.md).

Minimal production workflow:

1. Copy `docker-compose.prod.yml.example` to `docker-compose.prod.yml`.
2. Copy `backend/.env.prod.example` to `backend/.env.prod` and fill in real secrets.
3. Generate the backend encryption key at `backend/encryption_key`.
4. Start the stack with the production env file.
5. Run database migrations inside the backend container.

```bash
cp docker-compose.prod.yml.example docker-compose.prod.yml
cp backend/.env.prod.example backend/.env.prod
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > backend/encryption_key
docker compose --env-file backend/.env.prod -f docker-compose.prod.yml up -d
docker compose --env-file backend/.env.prod -f docker-compose.prod.yml exec backend alembic upgrade head
```

The image-based production template expects the environment file via `--env-file backend/.env.prod`, and the same values are also consumed inside the backend container.

## Additional Docs

- [`PROJECT_SPEC.md`](./PROJECT_SPEC.md): product scope, roadmap, and AI-agent working spec
- [`deployment.md`](./deployment.md): detailed production deployment guide
- [`evidence-seeker-setup.md`](./evidence-seeker-setup.md): seeker setup with Hugging Face Inference API
- [`evidence-seeker-configuration.md`](./evidence-seeker-configuration.md): configuration simplification spec

### 🏛️ Funding

Evidence Seeker Platform is funded by the *Federal Ministry of Education, Family Affairs, Senior Citizens, Women and Youth ([BMBFSFJ](https://www.bmbfsfj.bund.de/bmbfsfj/meta/en))*.

<a href="https://www.bmbfsfj.bund.de/bmbfsfj/meta/en">
  <img src="./funding.png" alt="BMBFSFJ Funding" width="40%">
</a>

## 📄 License

Evidence Seeker Platform is licensed under the [MIT License](./LICENSE).
