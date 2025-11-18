# Evidence Seeker Configuration Simplification Spec

## Background & Mission

- The Evidence Seeker Platform (see `README.md`) targets a September 2025 MVP that lets non-technical EVSE_ADMIN users stand up domain-specific fact-checkers without wrestling with the underlying EvidenceSeeker Python pipeline.
- Today configuration lives in `frontend/src/components/EvidenceSeeker/EvidenceSeekerConfig.tsx` and mirrors almost every key/value exposed by the backend (`backend/app/models/evidence_seeker_settings.py`). Users must understand embeddings, metadata filters, API keys, etc. before uploading documents or running fact checks.
- Because this environment is still a prototype, we are free to wipe the database and rewrite existing migrations. There is no need to preserve legacy Evidence Seekers or support data shape upgrades.
- We now want a default-first experience that:
  1. Reduces initial setup to “paste a Hugging Face API key and (optionally) declare who gets billed”.
  2. Ensures no Evidence Seeker can be used (documents, search, or fact-checks) before configuration is complete.
  3. Keeps an “expert mode” for teams that need overrides, but hides it unless explicitly requested.

## Current Experience & Pain Points

- **Scattered prerequisites** – API key creation happens in `APIKeyManager.tsx`, separate from seeker creation or configuration, so admins routinely create seekers they cannot actually run.
- **Overexposed fields** – `EvidenceSeekerConfig.tsx` surface >10 advanced knobs (`defaultModel`, `topK`, `metadataFilters`, etc.) with no defaults, while the backend already stores sensible defaults via `settings.evse_*`.
- **No enforcement** – Back-end endpoints in `backend/app/api/documents.py` and `backend/app/api/evidence_seekers.py` allow uploads, searches, and fact-check runs even if no Hugging Face key exists. Front-end tabs (`DocumentList`, `SearchInterface`, `EvidenceSeekerFactChecks`) have no guards, so users hit runtime errors later.
- **Fragmented flow** – `EvidenceSeekerForm.tsx` only collects title/description, then dumps users into management tabs where they must discover configuration separately.

## Target Experience

1. **Integrated creation wizard**
   - Step 1: Basic info (title, description, visibility) as today.
   - Step 2: “Connect inference” card prompting for a Hugging Face API key (name + key) and optional `bill_to` value. Validation occurs inline.
   - Step 3: Confirmation screen that creates the seeker, stores the key, applies defaults, and lands the user inside the management view with a “Configuration complete” badge.
   - Expert options (model overrides, metadata filters, etc.) are hidden behind an “Enable expert mode” toggle and only become visible after the simple setup succeeded.

2. **Configuration status baked into every workflow**
   - New `ConfigurationStatus` metadata (state enum, missing requirements list, configuredAt timestamp, simple/expert mode flag) returned with `GET /evidence-seekers/{id}/settings`.
   - Document pages (`DocumentList`, `DocumentUpload`) and analysis pages (`SearchInterface`, `EvidenceSeekerFactChecks`) check this status. If not “READY”, a modal blocks the screen and offers to launch the configuration flow without navigating away.
   - Evidence Seeker list rows show a badge (e.g., “Needs setup”) so admins can triage.

3. **Backend enforcement**
   - All write/read endpoints that require a working pipeline (document upload, reindexing, search, fact-check run create/rerun) perform a guard using the shared configuration service. The guard returns `409 Conflict` with a machine-friendly payload describing what is missing.
   - The guard uses defaults whenever possible; e.g., if no model is supplied, fall back to `settings.evse_default_model`, but a missing Hugging Face key will keep the seeker in `MISSING_CREDENTIALS`.

4. **Expert mode remains** but becomes opt-in per seeker, storing `setup_mode = "SIMPLE" | "EXPERT"` on the settings row. Expert mode reveals the existing advanced form and requires the user to acknowledge that they are bypassing the automatic defaults.

## Technical Plan

### Backend

#### Data model & migrations

1. **`backend/app/models/evidence_seeker_settings.py`**
   - Update the base model (and corresponding seed migration) directly since we can recreate the database. Add:
     - `setup_mode` (`String`, default `"SIMPLE"`).
     - `configured_at` (`DateTime`, nullable) for auditing.
     - `configuration_state` (`String`, default `"UNCONFIGURED"`) or separate `is_configured` boolean (state preferred for richer messaging).
     - `missing_requirements` (`JSONB`, default `'[]'`) to cache last validation result (optional but simplifies API responses).
   - Keep existing `embed_bill_to` column but make sure defaults allow `None`.
   - No incremental migration is required; we can modify the earliest EvidenceSeeker migration (e.g., `386798d9f88d_add_evidenceseeker_document_and_.py`) to include the new columns.

#### Config evaluation & guardrail service

1. Extend `backend/app/core/evidence_seeker_config_service.py`:
   - Add `ConfigurationStatus` dataclass/TypedDict describing `state`, `missing`, `setup_mode`, `blocking_reason`, `configured_at`.
   - Implement `evaluate_configuration(settings_row: EvidenceSeekerSettings) -> ConfigurationStatus` that checks:
     - `huggingface_api_key_id` exists and points to an active key.
     - `embed_bill_to` present iff platform requires billing (flag via `settings.evse_require_bill_to` or derived from environment).
     - Additional advanced requirements (if `setup_mode="EXPERT"`, allow empty key but require `pipeline_overrides` to set an alternative backend, etc.).
   - Cache status fields back onto the model (update `configuration_state`, `missing_requirements`, `configured_at`).
   - Expose `ensure_config_ready(db, seeker)` helper that calls `evaluate_configuration` and raises a domain exception if not in `READY`.

2. Update `backend/app/core/config_service.py`:
   - When creating a Hugging Face key via the wizard, infer a default key name (e.g., `"Default HF Key"`) and allow overriding.
   - Provide `get_active_hf_key(settings_row)` convenience for the evaluation helper.

#### API updates

1. **`backend/app/schemas/evidence_seeker_settings.py`**
   - Add `setupMode`, `configurationState`, `configuredAt`, and `missingRequirements` fields with camelCase aliases.
   - Extend `EvidenceSeekerSettingsUpdate` to accept `setupMode`, `embedBillTo`, and a boolean `simpleModeEnabled` for toggling expert mode.
   - Define a new `EvidenceSeekerConfigurationStatus` schema reused by guards and UI.

2. **`backend/app/schemas/evidence_seeker.py`**
   - Extend `EvidenceSeekerCreate` to accept an optional `initialConfiguration` payload containing:
     - `huggingfaceApiKey` (name + plaintext api_key)
     - `billTo`
     - `setupMode` defaulting to `"SIMPLE"`.
   - Extend `EvidenceSeekerRead` with a `configurationStatus` block (populated via `evaluate_configuration`).

3. **`backend/app/api/evidence_seekers.py`**
   - In `create_evidence_seeker`, wrap seeker creation + optional initial configuration inside a transaction:
     1. Insert the seeker.
     2. If `initialConfiguration.huggingfaceApiKey` exists, call `config_service.create_api_key` and assign `huggingface_api_key_id`.
     3. Call `evidence_seeker_config_service.upsert_settings` with defaults, `bill_to`, and `setup_mode`.
     4. Run `evaluate_configuration` and return the status in the response.
   - Modify `get_evidence_seeker_by_identifier` / `get_evidence_seekers` responses to include `configurationStatus`.
   - For endpoints that require configuration (document reindex, `/search`, `/runs` POST, `/documents/upload`, etc.), call `ensure_config_ready` and translate failures into HTTP 409 with detail `{state, missingRequirements}`.
   - Add `GET /evidence-seekers/{id}/configuration-status` endpoint (thin wrapper) so the front-end can poll without fetching the full settings payload.

4. **`backend/app/api/documents.py`**
   - Before uploads, downloads, deletions, or listings, enforce the readiness guard (readers should still view metadata, but uploads/deletes require `READY`).

5. **`backend/app/api/config.py`**
   - Accept a `link_to_settings` flag so newly created API keys can immediately update the corresponding `EvidenceSeekerSettings.huggingface_api_key_id`.
   - Return the updated `EvidenceSeekerSettingsRead` when the inline wizard completes.

6. **Tests**
   - Update `backend/tests/test_evidence_seeker_config_service.py` with new evaluation cases (missing key, missing bill_to, expert mode).
   - Extend API tests (`backend/tests/test_document_permissions.py`, `test_evidence_seeker_permissions.py`, etc.) to cover 409 conflicts when configuration is missing and success once ready.

### Frontend

#### Creation & onboarding flow

1. Replace `EvidenceSeekerForm.tsx` with a stepper:
   - Step 1 = existing basic info form.
   - Step 2 = new `ConnectInference` card embedding:
     - Inline API key inputs (provider fixed to Hugging Face, show key format hint). Keys are always stored per Evidence Seeker, so there is no dropdown of previously saved keys.
     - Optional billing field with tooltip explaining when required.
     - Expert mode toggle revealing advanced inputs (model dropdown, metadata filters, etc.).
   - On submit, call a new hook method `useEvidenceSeekers().createEvidenceSeekerWithConfig()` that hits the enhanced POST payload and handles both seeker + config creation atomically.
   - After success, navigate directly to `/evidence-seekers/:uuid/manage/documents`, but prefetch settings so the banner reads “Configuration ready”.

2. Add contextual education:
   - A side panel explaining why the Hugging Face key is required and linking to the HF docs.
   - Inline validation for key prefix (`hf_`) before the request is sent.

#### Management surfaces

1. **Status badges**
   - Update `EvidenceSeekerList.tsx` and `EvidenceSeekerManagement.tsx` headers to display `configurationStatus.state` (e.g., grey “Not configured”, yellow “Action needed”, green “Ready”).
   - Show `missingRequirements` text when hovered/clicked.

2. **Configuration guard modal**
   - New component `frontend/src/components/EvidenceSeeker/ConfigurationRequiredModal.tsx` that:
     - Accepts `state`, `missing`, and callbacks for “Configure now” or “Remind me later”.
     - Renders automatically inside `DocumentList`, `DocumentUpload`, `SearchInterface`, and `EvidenceSeekerFactChecks` when `configurationStatus.state !== "READY"`.
     - Uses `useEvidenceSeekerSettings` to trigger the inline wizard without navigating away (e.g., show the simple form as a dialog).

3. **Expert mode UI**
   - Refactor `EvidenceSeekerConfig.tsx` into two sections:
     - “Simple mode” card that only exposes a Hugging Face key input (always stored locally for this seeker), `bill_to`, and a read-only preview of defaults.
     - “Expert mode” accordion containing the current advanced JSON/text inputs. The accordion is disabled unless the user flips the `setup_mode` toggle and confirms.
   - When the user toggles expert mode off, warn that advanced overrides will be cleared/reset to defaults.

4. **Hooks & API layer**
   - Extend `frontend/src/hooks/useEvidenceSeekerSettings.ts` to:
     - Fetch and expose `configurationStatus`.
     - Offer `markConfigured()` helper that re-fetches status after any change.
   - Update `frontend/src/utils/api.ts` to support:
     - New POST shape for `/evidence-seekers`.
     - `GET /configuration-status`.
     - Guard-aware error typing for 409 responses (throwing a typed `ConfigurationError`).

5. **Shared context**
   - Provide `ConfigurationContext` or reuse `useEvidenceSeekers` so tabs do not individually fetch settings; the context caches status per seeker and invalidates when config updates succeed.

6. **Copy & notifications**
   - Success toast after configuration saves (“Ready to upload documents”).
   - Error toast when hitting a guarded endpoint, reusing the backend’s `missingRequirements` strings.

#### Visual polish

- Update Tailwind styles to keep the wizard consistent with `PageLayout`.
- Ensure modal works on mobile (fullscreen drawer) because some admins may configure from tablets.

### File-specific change list

**Backend**

| File | Change |
| --- | --- |
| `backend/app/models/evidence_seeker_settings.py` | Add `setup_mode`, `configuration_state`, `configured_at`, `missing_requirements`; ensure relationships updated. |
| `backend/alembic/versions/<timestamp>_add_configuration_state.py` | Migration adding the new columns and backfilling existing rows. |
| `backend/app/schemas/evidence_seeker.py` | Extend create/update/read schemas with `initialConfiguration` & `configurationStatus`. |
| `backend/app/schemas/evidence_seeker_settings.py` | Include new fields & `EvidenceSeekerConfigurationStatus`. |
| `backend/app/core/evidence_seeker_config_service.py` | Add evaluation helpers, guard, state persistence, and reuse them before building retrieval bundles. |
| `backend/app/api/evidence_seekers.py` | Update POST/GET handlers, add `/configuration-status`, and gate search/fact-check endpoints. |
| `backend/app/api/documents.py` | Guard uploads/deletes plus surface 409 responses. |
| `backend/app/api/config.py` + `backend/app/core/config_service.py` | Support inline Hugging Face key creation and automatic linking to settings. |
| `backend/tests/*` | New/updated tests covering status evaluation and guarded endpoints. |

**Frontend**

| File | Change |
| --- | --- |
| `frontend/src/components/EvidenceSeeker/EvidenceSeekerForm.tsx` | Convert to stepper collecting key + bill-to; call new create API. |
| `frontend/src/hooks/useEvidenceSeeker.ts` | Add `createEvidenceSeekerWithConfig` and expose configuration status in seeker list entries. |
| `frontend/src/utils/api.ts` | New request/response types for `initialConfiguration` and `configurationStatus`; handle 409s. |
| `frontend/src/types/evidenceSeeker.ts` | Define `ConfigurationStatus` interface and extend seeker/settings types. |
| `frontend/src/hooks/useEvidenceSeekerSettings.ts` | Surface `configurationStatus`, helper actions, and error typing. |
| `frontend/src/components/EvidenceSeeker/EvidenceSeekerConfig.tsx` | Split into simple/expert sections, with per-seeker key entry and inline creation. |
| `frontend/src/components/EvidenceSeeker/ConfigurationRequiredModal.tsx` (new) | Blocking modal invoked by tabs when configuration is incomplete. |
| `frontend/src/components/Document/DocumentList.tsx`, `DocumentUpload.tsx`, `Search/SearchInterface.tsx`, `EvidenceSeeker/EvidenceSeekerFactChecks.tsx` | Wrap content in guard logic; prompt configuration when needed. |
| `frontend/src/components/EvidenceSeeker/EvidenceSeekerManagement.tsx` & `EvidenceSeekerList.tsx` | Display status badges and CTA to configure. |

## Testing & Rollout

1. **Unit tests**
   - Backend: config evaluation helper, guard functions, and new API payload validation.
   - Frontend: component tests for the wizard (Vitest + React Testing Library) verifying step transitions and guard modal behavior.
2. **Integration tests**
   - Happy path: create seeker with key → upload document → run fact check.
   - Failure path: attempt to upload before config, expect 409 and modal.
3. **Environment validation**
   - After updating the base migrations, rebuild the local/staging database from scratch and ensure the “create seeker” wizard plus guards work end-to-end.
4. **Feature rollout**
   - Ship behind an environment variable (e.g., `ENABLE_SIMPLE_CONFIG=true`) if we need staged rollout; default ON in dev/staging, toggled in prod after QA sign-off.

## Risks & Open Questions

- **Multiple providers**: today we only require Hugging Face; if future seekers use OpenAI or Ollama, we need a generalized “credential requirement” registry. For now, spec assumes Hugging Face is mandatory for simple mode and that expert users know how to override backend type.
- **Bill-to requirement**: determine whether billing is globally required or per-tenant. Spec assumes a boolean flag in app settings; confirm with product.
- **Per-seeker credentials**: every Evidence Seeker stores its own encrypted Hugging Face key and billing metadata. There is no reuse across seekers, so we must clearly communicate this to admins in the UI to set expectations.

## TODO

- [ ] Design approval for the new wizard, status badge, and modal UX.
- [ ] Confirm backend bill-to requirement toggle semantics with product.
- [x] Implement backend schema changes + config evaluation helper (modify base migrations as needed).
- [x] Update seeker creation endpoint & schemas for `initialConfiguration`.
- [x] Wire up frontend wizard + guard components.
- [ ] Add automated tests (backend + frontend) for the guarded flows. *(Backend unit tests updated; frontend test coverage still pending.)*
- [x] Document operational steps (e.g., how to rotate Hugging Face keys) in `README.md`.

## Progress

- [x] Specification drafted (this document).
- [x] Engineering implementation in progress (backend enforcement + frontend UX shipped in this iteration).
- [ ] QA + rollout pending.
