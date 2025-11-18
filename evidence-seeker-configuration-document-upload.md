# Evidence Seeker Configuration — Document Upload Spec

## 1. Background & Motivation
- The configuration simplification project (see `evidence-seeker-configuration.md`) delivered a three-step wizard that guarantees every Evidence Seeker is provisioned with valid inference credentials before use.
- MVP feedback: new admins still land on an empty seeker after the wizard and must discover the Documents tab to upload sources manually. This delays the first “aha” moment and defeats the purpose of a guided setup.
- Goal: extend the wizard so that document ingestion happens during onboarding. When a user clicks “Finish setup”, the seeker must already contain at least one processed document so the Fact Check/Test interface works immediately.

## 2. Objectives
1. **Prompt for documents before completion** — Wizard flow requires either (a) ≥1 successful upload or (b) an explicit “Skip, finish later” acknowledgement that leaves the seeker in a `MISSING_DOCUMENTS` state.
2. **Reuse the production uploader** — Leverage the existing `DocumentUpload` stack (dropzone, validation, progress) so onboarding stays consistent with the Documents tab.
3. **Keep guardrails intact** — Back-end `ConfigurationStatus` should treat “no documents yet” as its own unmet requirement and block search/fact-check APIs until at least one document is active.
4. **Streamline first-run experience** — As soon as the wizard completes, the seeker shows READY status, embeddings are queued/complete, and the user is dropped into the Fact Check UI with guidance to run their first manual evaluation.

## 3. Non-Goals
- Rewriting the document pipeline, vector store, or file size limits.
- Supporting additional file types beyond the existing `.pdf` / `.txt` pair.
- Automating fact-check runs or benchmark statements during setup (out-of-scope).

## 4. Success Criteria
- ≥90% of newly created seekers reach READY in a single wizard session (instrumented).
- Median time from “Create seeker” to first successful fact check < 3 minutes.
- No regressions to standalone document management workflows.

## 5. User Flow Updates
| Step | Current | New Requirement |
| --- | --- | --- |
| 1. Basics | Title, description, visibility. | No change. |
| 2. Connect inference | Hugging Face key + billing. | Show next-step reminder that documents are required. |
| 3. Documents *(new step)* | — | Inline uploader (multi-file) + status list showing queued/processing/ready. Finish button disabled until requirement met. |
| 4. Review | Summary + confirm. | Moves to Step 4. Shows document checklist (count, failures). Displays warning if user opted to skip uploads. |

### Step 3 UX Requirements
- Drag-and-drop zone + “Browse files” button (reuse `DocumentUpload.tsx` dropzone config).
- Display table/list of files with columns: Name, Size, Status (Queued, Uploading, Embedding, Ready, Failed) and retry/remove actions.
- Surface validation errors inline (file type, size, duplicate).
- “Continue without documents” secondary action opens confirmation modal describing consequences and sets `documentSkipAcknowledged=true`.
- Primary “Continue” remains disabled until either (a) at least one document reaches `Ready` OR (b) skip is confirmed.

### Step 4 Review UX Updates
- Card summarizing: inference credentials ✅, documents ✅/⚠, pending embeddings count.
- If skip pathway chosen, Finish button text changes to “Finish with missing documents” and final call-to-action routes user directly to the Documents tab.
- After successful finish (no missing documents), automatically navigate to the Fact Check/Test tab and trigger an onboarding tooltip instructing the admin to run their first fact check; do not pre-fill or auto-run any claims.

## 6. Backend Requirements
1. **Configuration status enumerations**
   - Extend `ConfigurationState` enum with `MISSING_DOCUMENTS`.
   - `ConfigurationService` marks seekers as `READY` only if credentials validated *and* `documents.count > 0`.
2. **Wizard uploads before READY**
   - Allow `POST /evidence-seekers/{id}/documents` when `configuration_state` in `{UNCONFIGURED, CREDENTIALS_VALID}` provided the request includes `onboardingToken` emitted by wizard creation (short-lived JWT stored client-side). This bypass prevents the existing guard from blocking uploads during the wizard.
   - Once documents exist, standard guards apply and onboarding token is discarded.
3. **Skip acknowledgement**
   - Persist `document_skip_acknowledged` boolean on settings table (default `false`) to record intent and inform status messaging/UI badges.
4. **Instrumentation**
   - Emit events `evse_onboarding_document_uploaded`, `evse_onboarding_skip_documents`, `evse_onboarding_ready` to `ProgressTracker` so we can compute funnel metrics.

## 7. Frontend Architecture
- Create `WizardDocumentStep.tsx` in `frontend/src/components/EvidenceSeeker/Wizard` that wraps `DocumentUpload` hook logic but swaps layout/style for wizard context.
- Introduce shared `useDocumentUploadController` hook to encapsulate:
  - File queue state machine (`idle -> uploading -> embedding -> ready/error`).
  - Aggregated requirement status `hasReadyDocument`.
  - Skip confirmation helpers.
- Update `EvidenceSeekerManagementWrapper` to read `configurationStatus.missingRequirements` and display `MISSING_DOCUMENTS` badges anywhere status is surfaced (list cards, headers, guard modals).
- Ensure `DocumentList` and `SearchInterface` already respect the guard; update copy to highlight next action: “Complete setup by uploading at least one document via Configuration”.

## 8. API & Data Contracts
```ts
// New field on ConfigurationStatus DTO
type ConfigurationStatus = {
  state: 'UNCONFIGURED' | 'MISSING_CREDENTIALS' | 'MISSING_DOCUMENTS' | 'READY' | 'ERROR';
  missingRequirements: Array<'CREDENTIALS' | 'DOCUMENTS' | 'OTHER'>;
  configuredAt?: string;
  setupMode: 'SIMPLE' | 'EXPERT';
  documentSkipAcknowledged: boolean;
};

// Wizard token returned after Step 2
POST /evidence-seekers
→ { seekerId, onboardingToken }
```
- Document upload endpoint accepts optional header `X-Onboarding-Token`. Backend validates token -> seeker -> user permissions.
- Finishing wizard calls `POST /evidence-seekers/{id}/finish-onboarding` which:
  1. Recomputes configuration state.
  2. Revokes onboarding token.
  3. Returns final status payload for UI navigation logic.

## 9. Validation & Edge Cases
- **Slow embeddings**: Show “Processing” indicator with ability to proceed once upload succeeded even if embeddings still running, provided at least one document reached “upload complete” (not necessarily embedded). However, backend READY state still waits for embedding jobs to complete; UI should poll status every 5s until READY to avoid confusing users.
- **Upload failures**: Retry button reuses existing API. If reattempt fails twice, show CTA linking to Documents tab help article.
- **Skip after upload**: If user uploaded files but all failed, they can still skip; system records both failures and skip flag for analytics.
- **Wizard abort**: If user closes wizard mid-step, onboarding token stays valid for 24h. Subsequent visits resume at documents step with existing queue state fetched from `/documents` API.

## 10. Decisions & Follow-ups
1. **Minimum documents** — READY requires ≥1 successful document; no higher minimum for MVP.
2. **Abandoned uploads** — Do not auto-delete partially uploaded files yet; revisit when real usage surfaces issues.
3. **Post-setup CTA** — Fact checking is the primary action, so finishing the wizard routes users to the Fact Check/Test view with guidance to run their first evaluation manually.
4. **Sample claims** — No automatic sample fact check or auto-filled prompts; admins must enter their own claim before running the pipeline.
