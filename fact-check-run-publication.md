# Fact Check Run Publication Plan

## 🎯 Goals
- Give EVSE admins full control over which fact check runs become public artifacts.
- Support deleting unwanted runs from the admin console.
- Allow each Evidence Seeker to choose between auto-publishing (current behavior) and manual publishing where runs stay unlisted until explicitly featured.

## 🔍 Requirements Recap
1. **Run deletion:** platform/Evidence Seeker admins can permanently remove a run (including its evidence) from both admin and public surfaces.
2. **Publication modes per seeker:**
   - `AUTOPUBLISH`: successful runs behave exactly like today (instantly public and listed).
   - `MANUAL`: runs still execute and have shareable URLs for the requester, but they are hidden from discovery feeds until an admin features them.
3. **Manual mode expectations:**
   - The requester can open `/fact-checks/{run_uuid}` once the run succeeds and share that link.
   - Public landing pages (home + seeker detail) only show “featured” runs selected by admins.
   - Admins can promote/demote a run at any time.

## 🧱 Current Behavior Snapshot
- `FactCheckRun` has boolean `is_public` and `published_at` fields. All successful runs flip both as part of `evidence_seeker_pipeline`.
- Public APIs (`GET /fact-checks`, `GET /fact-checks/{uuid}`, seeker detail page) filter strictly on `is_public = true` and `status = SUCCEEDED`.
- Admin APIs expose listing, detail, rerun, and cancellation, but there is no deletion endpoint and no publish controls.

## 🏗️ Proposed Architecture

### 1. Publication Mode per Evidence Seeker
- **Schema:** add `fact_check_publication_mode` (`AUTOPUBLISH` | `MANUAL`) on `evidence_seekers` (default `AUTOPUBLISH`). Include Alembic migration + SQLAlchemy enum + Pydantic/typescript fields.
- **Settings API/UI:** extend `EvidenceSeekerUpdate` (backend schemas + `useEvidenceSeeker` hook) so admins can flip the mode alongside the existing `isPublic` toggle. Add a “Fact check publication” section in `EvidenceSeekerSettings.tsx` with radio buttons describing both modes and a tooltip linking to this doc.
- **Business rule guardrails:** when a seeker is private (`is_public = false`), manual mode still applies so admins can curate visibility before making the seeker public later.

### 2. Fact Check Run Visibility Lifecycle

#### Data model additions
- Introduce `FactCheckRunVisibility` enum (`PUBLIC`, `UNLISTED`, `PRIVATE`) on `fact_check_runs.visibility` with default `PUBLIC`. Add `featured_at`, `featured_by_id`, `deleted_at`, `deleted_by_id`, and nullable `deletion_reason`.
- Keep the existing `is_public` flag for backward compatibility but treat it as derived: set `is_public = (visibility = PUBLIC)` whenever a run transitions.
- Add SQLAlchemy relationships for `featured_by`/`deleted_by` → `User` to simplify audit logs.

#### Run creation logic
- Update `EvidenceSeekerPipelineManager.create_fact_check_run` to set initial `visibility` based on seeker mode:
  - `AUTOPUBLISH`: `visibility=PUBLIC`, `published_at=completed_at` (current behavior).
  - `MANUAL`: `visibility=UNLISTED`, leave `published_at` null. The requester still receives `run.uuid` so their share link works.
- Use a helper (`_apply_publication_transition`) that sets `is_public`, `visibility`, and timestamps consistently, and call it from both admin and public run paths.

#### Manual promotion/demotion APIs
- New endpoint `POST /evidence-seekers/{id}/runs/{run_uuid}/publication` with payload `{ "visibility": "PUBLIC" | "UNLISTED" }`. Only EVSE admins and platform admins may call it. The handler:
  - Validates seeker ownership and run status (`SUCCEEDED` only for PUBLIC).
  - When promoting to `PUBLIC`, set `published_at` (if missing) and `featured_at = now`, `featured_by_id = current_user.id`.
  - When demoting to `UNLISTED`, clear `featured_at`, `featured_by_id`, `published_at`, and force `is_public = False`.
- The admin UI will expose these actions as “Feature run” / “Remove from featured”.

#### Run deletion
- Add `DELETE /evidence-seekers/{id}/runs/{run_uuid}/delete` (distinct from the existing cancellation endpoint). Behavior:
  - Soft delete via `deleted_at`/`deleted_by_id`, wipe `is_public`, `visibility`, and `published_at`, and cascade delete `FactCheckResult` + `FactCheckEvidence` rows to reclaim storage.
  - Cancel any outstanding background tasks (if still running) via `progress_tracker`.
  - Return `204` so the UI can remove the item.
- Extend admin list queries to exclude deleted rows by default but allow optional `?includeDeleted=true` for future audits.

#### Public API adjustments
- `GET /fact-checks` and seeker detail pages only include runs where `visibility = PUBLIC`, `deleted_at IS NULL`, `status = SUCCEEDED`.
- `GET /fact-checks/{uuid}` should:
  - Return runs that are `visibility IN ('PUBLIC','UNLISTED')`, not deleted, and belong to a public Evidence Seeker.
  - Ensure we never expose `PRIVATE` or deleted runs (return 404).
- Update `PublicFactCheckRunSummary` to include an optional `featuredAt` for future highlighting, though the immediate UI can keep the current layout.

### 3. Frontend Deliverables

#### Admin management (React)
- `EvidenceSeekerFactChecks.tsx`
  - Extend the run table to show a “Visibility” column (Badges for `Featured`, `Unlisted`, `Deleted`).
  - Add action buttons: `Feature`, `Remove from featured`, `Delete run`. Disable invalid actions (e.g., can’t feature a failed run).
  - Surface confirmation modals and optimistic UI updates by mutating the `runs` state after API responses.
- `useEvidenceSeekerRuns.ts`
  - Add `updatePublication` and `deleteRun` helpers calling the new endpoints.
  - Refresh run lists after successful mutations.

#### Evidence seeker settings
- `EvidenceSeekerSettings.tsx`: new radio/button group for “Fact Check Publication Mode” tied to backend field.
- Include inline copy describing:
  - `Autopublish`: “Successful fact checks instantly appear on the public home page and seeker landing page.”
  - `Manual`: “Runs stay unlisted. Requesters keep a shareable link, and admins can feature selected runs later.”

#### Public Experience
- `frontend/src/pages/public/PublicHomePage.tsx` and `PublicEvidenceSeekerPage` should already consume `recentFactChecks`; ensure those API responses exclude unlisted entries so no UI work is needed besides verifying fallback empty states.
- `PublicFactCheckPage` should gracefully handle unlisted runs (no “Featured” tags). Add a subtle banner saying “This fact check is unlisted — only people with this link can view it.” when `visibility=UNLISTED` in the payload.

### 4. Testing & Validation

**Backend**
- Alembic migration unit test to verify enum + defaults + data backfill (`fact_check_runs.visibility='PUBLIC'`) for existing data.
- API tests:
  - Creating runs in both modes sets the correct visibility.
  - Manual promotion toggles `is_public`, `published_at`, `featured_at`, and shows up on `/public/fact-checks`.
  - Unlisted run is retrievable by UUID but absent from `/public/fact-checks`.
  - Deleted run returns 404 everywhere (admin detail, public endpoints).
- Permission tests covering EVSE admin vs reader vs anonymous.

**Frontend**
- Component tests (or RTL unit tests) covering:
  - Publication mode toggle persisting its state.
  - Feature/unfeature/delete buttons showing and invoking the right hooks.
  - `PublicFactCheckPage` banner when payload indicates unlisted visibility.

### 5. Rollout Plan
1. Ship backend migration + API changes (deploy with feature flag if needed).
2. Backfill existing seekers to `AUTOPUBLISH` and runs to `PUBLIC`.
3. Release frontend toggles and admin controls.
4. After verification, communicate to admins how to switch seekers to manual mode and how to feature runs.

This plan delivers the requested control while maintaining shareable links for manual mode and keeping the public catalog curated by admins.
