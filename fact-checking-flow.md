# Public Fact-Checking Flow Improvements

## Goals
- Remove the awkward “Starting run…” state on `PublicEvidenceSeekerPage` by sending visitors straight to the detail route for the run they just launched.
- Make `PublicFactCheckPage` feel alive: show that a run is processing, refresh its status automatically, and reveal interpretations/evidence the moment the backend persists them.
- Keep behavior in sync with authenticated fact-check flows so visitors get the same lifecycle (PENDING → RUNNING → terminal) even though they are anonymous.

## Constraints / Technical Considerations
- Public users **cannot** call `/progress/operations/{id}` because that endpoint requires authentication tied to the user who owns the run. Public runs store `user_id=0`, so reuse of `ProgressIndicator` is not possible without exposing a new unauthenticated progress API.
- The only public surface that exposes run state is `GET /public/fact-checks/{run_uuid}`. The response includes `run.status`, timestamps, and `results`. That endpoint must be polled to learn when a run finishes.
- Backend statuses already mirror the private flow (`FactCheckRunStatus` + `errorMessage` fields). As soon as the pipeline saves interpretations, the same GET endpoint returns them, so frontend polling is sufficient—no backend work is required unless we later want public WebSocket push.

## Target UX Flow
1. User enters a claim on `PublicEvidenceSeekerPage` and hits “Run fact check”.
2. After `createFactCheckRun` resolves:
   - Immediately navigate to `/fact-checks/{run.uuid}` (optionally pass `state` or hash so we can auto-scroll to the progress area).
   - The form resets so the landing page stays clean if the user navigates back.
3. `PublicFactCheckPage` loads and:
   - Shows a hero section with the statement plus a **progress card** when `run.status` is `PENDING` or `RUNNING`.
   - Polls `publicAPI.getFactCheck(runUuid)` every ~3 seconds (faster than existing private refresh, but respectful of rate limits).
   - Each poll updates `run` + `results`. Once status enters `SUCCEEDED`, `FAILED`, or `CANCELLED`, stop polling.
   - If status is terminal but `errorMessage` exists, surface it in the alert already present on the page.
4. As soon as `results.length > 0`, the interpretations and evidence sections populate automatically with no page refresh.

## Frontend Changes

### `PublicEvidenceSeekerPage.tsx`
- Inside `handleFactCheckSubmit`, after successfully creating the run:
  - Drop the `submittedRun` success banner and replace it with `navigate(`/fact-checks/${run.uuid}`, { state: { fromSeeker: seekerUuid } })`.
  - Keep error handling the same; only the happy path changes.
  - Optionally keep the CTA copy (“Runs finish asynchronously…”) but clarify in helper text that visitors are redirected to a live progress view.

### `PublicFactCheckPage.tsx`
- State management:
  - Track `polling` vs `loaded` booleans so we can show a spinner even after the initial fetch.
  - Store the interval ID so it can be cleaned up on unmount and when a run reaches a terminal status.
- Data fetching:
  - Extract the existing fetch logic into `fetchRunDetail` and call it both on mount and from the polling interval.
  - Poll every 3 seconds while status is `PENDING` or `RUNNING`. If the first response is already terminal, skip polling.
  - Use `setData` with functional updates to avoid flicker when results arrays are identical.
- Progress indicator:
  - Add a new lightweight component (inline JSX is fine) that renders when `run.status` is non-terminal:
    - Show an animated `Loader2` icon, the current backend status (`PENDING` ⇒ “Queued”, `RUNNING` ⇒ “Analyzing evidence”), and the timestamp of the last update.
    - Surface helper text (“Stay on this page—results update automatically.”).
  - When polling detects progression from `PENDING` → `RUNNING`, update the copy to reflect that change.
- Result auto-refresh:
  - Because we now repopulate `data` on each poll, the existing JSX for interpretations/evidence automatically re-renders. No extra special casing is needed beyond guarding against duplicates.
- Error handling:
  - If polling fails (network error), keep the last known data but show a dismissible inline warning asking the user to retry.
  - If the backend ultimately marks the run as `FAILED`/`CANCELLED`, stop polling and ensure the alert block includes the backend-provided `errorMessage`.

## Backend Touchpoints
- No endpoint changes are required. We simply reuse `POST /public/evidence-seekers/{uuid}/fact-checks` and `GET /public/fact-checks/{run_uuid}`.
- If we later want richer progress for anonymous users, we would need either:
  1. A public read-only projection of `/progress/operations/{operation_id}` that authorizes via the `run_uuid`.
  2. Server-sent events/WebSocket channel keyed by the run UUID.
  These are out of scope for this iteration but noted here because the frontend polling loop should be implemented so it can be swapped for push updates later (e.g., extracted into a hook).

## Open Questions / Follow-Ups
- Should public polling have a hard timeout (e.g., after 2 minutes show a “Still running, refresh later” message)? Current spec keeps polling until the tab closes or status becomes terminal.
- Do we want to highlight the operation ID anywhere for debugging? The API returns it, but we currently hide it for public visitors.
- Once this flow ships we should add a regression test plan covering: redirect works, spinner shows for RUNNING, completed runs stop polling immediately, and failed runs surface errors.
