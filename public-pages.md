# Public Pages & Visibility Spec

## 🎯 Purpose
Ship Iteration 4's "Public/Private Logic" and "Public Pages" so that (a) Evidence Seeker owners can intentionally publish their work and (b) unauthenticated visitors can browse, run, and share public fact checks without touching the admin interface.

## 📦 Scope
1. **Public/Private Logic** – data model, API, and authorization rules that determine what becomes discoverable.
2. **Public Pages** – the unauthenticated UI surfaces (Homepage, Evidence Seeker profile, Fact Check detail) that consume the new public data.

---

## 1. Public/Private Logic

### 1.1 Visibility States (Existing)
| Flag | Description | Where it lives |
| --- | --- | --- |
| `is_public = false` | Internal-only seeker. Visible to logged-in users with permissions. | `evidence_seekers.is_public` (already in DB + UI toggle). |
| `is_public = true` | Published seeker. Listed on homepage and available to anonymous visitors. | Same boolean flag above. |

No stretch/unlisted state in this iteration.

### 1.2 Data Model Touch Points
*Implementation note: this is a prototype, so we can edit the original Alembic migrations / base schema directly and discard existing data instead of generating incremental migrations.*
- **EvidenceSeeker**
  - Reuse `is_public` flag controlled by the existing Publish toggle in the admin UI.
  - Add `published_at TIMESTAMPTZ NULL` (optional but useful for sorting/metrics). Auto-set when `is_public` flips to true, null when reverting to private. (This can go straight into the existing base migration since we’re fine rewriting history.)
  - Continue using the existing `description` field for public copy; no extra summary column.
  - Public URLs use the already-present `uuid` (no new slug field needed right now).
- **FactCheckRun**
  - Add `is_public BOOLEAN DEFAULT FALSE` that snapshots the parent seeker’s `is_public` at run completion. Keeps historical runs accessible even if seeker is later hidden.
  - Add `published_at TIMESTAMPTZ NULL` mirroring the seeker toggle for auditability.
- **Documents**
  - No schema changes for now. When a seeker is public, document metadata becomes visible on the public profile, but downloads remain locked unless/until we add per-document controls.

### 1.3 State Transitions & Permissions
1. **Who can publish?** PLATFORM_ADMIN or *any* EVSE_ADMIN who has manage access to that seeker (not only the creator). Enforce via existing permissions table.
2. **Publishing flow** (simple):
   - Toggle `is_public` on → set `published_at=now()`.
   - Queue cache invalidation for homepage + seeker profile.
   - Fire audit log event (`evidence_seeker_published`).
3. **Unpublish flow**:
   - Toggle `is_public` off → set `published_at=NULL`.
   - Derived fact check routes respond with 404 + friendly "no longer public" message.
4. **Fact Check Runs**:
   - When a public visitor runs a fact check, mark resulting run `is_public=true`.
   - Existing private runs keep `is_public=false` even if seeker is later published to avoid accidental leakage. Only runs explicitly generated via public surface (or manually exposed by admin) should be public.

### 1.4 API & Permissions
- `PATCH /api/evidence_seekers/:id/publish`
  - Body `{ is_public: boolean }`.
  - Checks permission + flips boolean + timestamps as above.
- `GET /api/public/evidence_seekers`
  - Params: `page`, `page_size`, `search`, `tag`.
  - Returns only seekers where `is_public=true`.
- `GET /api/public/evidence_seekers/:uuid`
  - Payload: title, description, logo, stats, safe config summary, plus document metadata if seeker is public.
- `POST /api/public/evidence_seekers/:uuid/fact-checks`
  - Public execution entry point. All EVSE-specific throttles apply. No auth header.
- `GET /api/public/fact-checks/:runUuid`
  - Returns runs where `is_public=true`.
- Authenticated routes keep using `PermissionGuard`. Public routes use IP throttling + request logging middleware.

### 1.5 Caching & Performance
- Homepage aggregate cached for 60s (Redis or FastAPI cache decorator).
- Seeker profile JSON cached per `uuid` for 30s; bust when publish toggle flips or documents change.
- Fact check detail cached per run for 5 minutes; bust when status changes.

---

## 2. Public Pages

### 2.1 Shared UX Requirements
- Public routes live under `/public/*` and bypass Auth layout.
- Use existing design tokens + typography; no dashboard chrome.
- Provide SEO-ready metadata (title/description/OpenGraph) and canonical URLs.
- Respect dark/light modes but default to light for first load.
- All CTAs funnel to `/register` or `/login` depending on context.

### 2.2 Page Map
| Route | Purpose |
| --- | --- |
| `/` (Homepage) | Marketing landing + discovery of public Evidence Seekers & fact checks. |
| `/evidence-seekers/:uuid` | Public profile for one seeker with run UI. |
| `/fact-checks/:runUuid` | Deep link to a specific fact check result. |

#### 2.2.1 Homepage
**Hero Section**
- Headline explaining Evidence Seeker value.
- CTA buttons: `Create an Evidence Seeker` (→ onboarding) and `Explore Evidence Seekers` (scroll to directory).
- Background image or subtle animation referencing verification theme.

**Latest Fact Checks**
- Grid/list of the 4-6 most recent *public* fact checks across all seekers.
- Show claim text, verdict badge, seeker name, timestamp, and `View Details` link.
- Each card includes micro-copy like "Backed by 12 documents" pulled from run summary.

**Featured Evidence Seekers**
- Two lists:
  - `Most Active` (highest fact check count last 7 days).
  - `Popular Topics` (manual curation via tag or admin flag).
- Each card: logo, name, short summary, doc count, `Test this Seeker` button linking to profile.

**Create Your Own CTA**
- Section describing 3 steps to build a seeker, with bullet icons.
- Button to `/register` (if unauthenticated) or `/dashboard/evidence-seekers/new`.

**Footer**
- Links to docs, privacy, contact, GitHub.

#### 2.2.2 Evidence Seeker Public Profile (`/evidence-seekers/:uuid`)
**Header**
- Logo/avatar, name, tags, publish date, "Maintained by" (organization or anonymized if not provided).
- Primary action: `Run a Fact Check` (scrolls to form).
- Secondary: `Share` (copy URL).

**Tabs / Sections**
1. `Overview`
   - Uses existing admin description + any metadata we already collect (no new authoring fields).
   - Show configuration highlights (LLM model, retrieval depth) only if marked safe for public.
2. `Run Fact Check`
   - Textarea + optional context fields mirroring internal testing UI but simplified.
   - Toggles for `Quick Check` vs `Deep Dive` (calls same backend with different params).
   - Show progress indicator, friendly errors, and link to result detail on success.
3. `Fact Check History`
   - Table of recent public runs (claim, verdict, date, run duration).
   - Pagination + filters (verdict type, timeframe).
4. `Documents`
   - Visible whenever the seeker is public.
   - Document cards show title, source, uploaded date, optional short summary; downloads stay internal-only until we add per-document controls (show disabled button + tooltip explaining why).

**Access Guardrails**
- If seeker becomes private mid-session, all sections show `This Evidence Seeker is no longer public` + CTA to register.

#### 2.2.3 Fact Check Detail (`/fact-checks/:runUuid`)
**Hero**
- Verdict badge (e.g., `Supported`, `Needs More Evidence`, `Refuted`), claim text, run timestamp, and associated Evidence Seeker link.

**Reasoning Timeline**
- Step-by-step explanation from pipeline (claim parsing → retrieval → analysis).
- Each step collapsible with raw model output behind "Show reasoning" toggle to avoid overwhelming casual readers.

**Evidence Panel**
- List of cited documents with snippet, confidence score, and link to document (if public) or message `Source available to members only`.
- Provide share anchors per citation for deep linking.

**Result Metadata**
- Inputs used (temperature, retrieval depth), run duration, model version.
- `Share` button copying canonical URL.

**Next Actions**
- Buttons: `Run a New Fact Check with this Seeker`, `Report an Issue` (email link/form).

### 2.3 Technical Notes
- All authenticated dashboard routes live under `/app/*`. This keeps `/`, `/evidence-seekers/:uuid`, and `/fact-checks/:runUuid` public even when an admin session is active, and it gives us a single mount point for auth guards + dashboard chrome.
- Public routes live in a new `frontend/src/pages/public/` directory with dedicated layout.
- Data fetching via new `publicApiClient` instance (no auth headers).
- Use React Query cache keys `['public', 'evidenceSeekers']`, etc., to share data between homepage and profile.
- Server should set cache-control headers for GET endpoints (e.g., `s-maxage=60`) to enable CDN later.
- Analytics events tagged as `public_*` to isolate funnel metrics.

---

## ✅ Deliverables Checklist
- [ ] TODO: adjust the initial migration files (and any ORM models) to include `published_at`/`is_public` fields.
- [ ] Update existing base migrations/schema definitions with `published_at` + fact-check visibility fields (no new migration files needed).
- [ ] Backend validators/tests for visibility transitions and public endpoints.
- [ ] Rate limiting + logging middleware applied to `/api/public/*`.
- [ ] Frontend routes, components, and copy for Homepage, Seeker profile, Fact Check detail.
- [ ] Feature flag (env `ENABLE_PUBLIC_PAGES`) wrapping entire surface for controlled rollout.
- [ ] QA scenario doc covering publish/unpublish, doc access, fact check sharing, and regression tests for private flows.
- [ ] Regression checklist for the `/app` split: logged-out homepage, logged-in homepage, switching via the dashboard "View Public Site" link, and returning via the public "Go to Dashboard" CTA.
