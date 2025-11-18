# Evidence Seeker Wizard Hardening

## Background

While testing the three-step setup wizard we discovered that the UI frequently resets to step 1 and loses all state if a user pauses to gather information or files. The reset is triggered by global polling loops firing while the user is idle:

1. `AuthContext` polls `/permissions/me` every 60 s and again on every tab-focus event. When the one-hour JWT expires, the next poll receives `401`, the axios interceptor wipes `localStorage` and hard-navigates to `/login`, unmounting the wizard (`frontend/src/context/AuthContext.tsx:12-241`, `frontend/src/utils/api.ts:31-79`, backend token lifetime `backend/app/core/config.py:15-19`).
2. On the document step, `WizardDocumentStep` instantiates `useDocumentUploadController` which in turn creates a 5 s polling loop for index jobs even when no upload is running (`frontend/src/hooks/useDocumentUploadController.ts:41-117`, `frontend/src/hooks/useIndexJobs.ts:40-84`). Any 401/500 during that poll has the same global effect.
3. All wizard form data is held in local component state and cleared whenever the component remounts (`frontend/src/components/EvidenceSeeker/EvidenceSeekerForm.tsx`), so even benign refreshes wipe progress.

## Goals

1. The wizard must never lose entered data because of background polling or token refresh.
2. Polling during onboarding should be suspended when it is not strictly necessary (inactive tab, idle uploads).
3. Authentication expiry should surface a blocking modal or toast that lets the user re-authenticate without destroying the SPA.
4. Wizard progress (step, text fields, skip acknowledgement, onboarding token) should survive reloads and route changes for at least the token lifetime.

## Proposed Technical Steps

### 1. Decouple Auth Expiry Handling

- Replace the axios interceptor redirect with an event dispatch: e.g. emit `sessionExpired` through a shared store or callback in `AuthContext` instead of calling `window.location.href = "/login"`.
- In `AuthProvider`, listen for that event and set `authState.isAuthenticated = false`, show a modal that contains the login form, and block navigation until the user re-authenticates. Ensure we keep the existing React tree mounted so wizard state is untouched.
- Only purge `localStorage` after the user confirms logout or after a successful re-login; otherwise keep the previous `Wizard` step information accessible for persistence (see step 3).

### 2. Tame Permission Polling

- `AuthContext`: gate the 60 s permission poll behind document visibility AND wizard activity.
  - Introduce a `usePageActivityTracker` hook that exposes `isIdle` (tab hidden or no user interaction for N minutes). Skip polling when idle.
  - Add exponential backoff and stop permanently after the first 401; rely on the session-expired handler instead.
- Provide a manual `refreshPermissions` button near the management UI so users can trigger sync without constant background traffic.

### 3. Pause Index Job Polling During Wizard Idle

- Update `useDocumentUploadController` to only opt into index-job polling (`useIndexJobs(..., pollIntervalMs)`) when there is at least one queue item with status `uploading` or `embedding`.
- After the queue drains, stop polling and restart only if a new upload is enqueued. Also pause polling when `document.hidden === true`.
- Ensure that failed polling requests no longer bubble up to the global axios interceptor as fatal errors: catch and suppress 401s while the wizard is idle and instead surface a retry button within the document step.

### 4. Persist Wizard Drafts

- Introduce a `useWizardDraft` hook that syncs `details`, `credentials`, `step`, `skipAcknowledged`, `onboardingToken`, and `wizardSeeker.uuid` to `sessionStorage` (JSON payload keyed by user ID).
- On mount, hydrate the form from this draft. After any step advancement or API success, update the stored draft. Clear it after `finishOnboarding` completes.
- For sensitive data:
  - Only keep `credentials.apiKeyValue` in memory; if the user navigates away, require re-entry. Store a flag indicating the step is complete so we can route directly to documents while prompting for the key again if needed.

### 5. Backend Support Tweaks

- Confirm JWT lifetime is acceptable; consider extending to 4h for admins if there are no compliance constraints (`settings.jwt_expiration`).
- If we cannot extend lifetime, add refresh-token support to avoid forced logout while the wizard is open.
- Optionally emit wizard progress checkpoints via a `PATCH /evidence-seekers/{uuid}/wizard-draft` endpoint so the backend can restore state even if the UI state is lost or the user switches devices.

### 6. Regression Coverage

- Add Vitest component tests for `EvidenceSeekerForm` verifying:
  - Draft state survives `window.location.reload()` by mocking `sessionStorage`.
  - Token-expiry events show the re-auth modal without unmounting the wizard.
  - Index-job polling pauses when queue is empty and resumes when new files are added.
- Add Cypress (or Playwright) end-to-end scenario: start wizard, wait 70 minutes (or simulate token expiry by clearing cookies), validate that the wizard prompts for login but keeps form fields intact.

## Rollout Plan

1. Implement client changes (Sections 1–4) behind a feature flag `WIZARD_STATE_GUARDS` for quick rollback.
2. Deploy backend adjustments (Section 5) with feature flag alignment (`ENABLE_TOKEN_REFRESH` etc.).
3. Release to staging; run regression tests; simulate session expiry to verify modals and persistence.
4. Monitor production logs for `sessionExpired` events and wizard completion rates to ensure improvement.

