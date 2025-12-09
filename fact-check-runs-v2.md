# Fact Check Runs V2 – Public UI for Sources & Excerpts

## Goal
Expose evidence sources on public fact-check runs with progressive disclosure (avoid overload, enable deep dives). Leverage EvidenceSeeker result payloads (interpretations + documents + metadata) and surface confirmation scores per source.

## Data Model & Backend Facts
- EvidenceSeeker -> `_extract_interpretations` (`backend/app/core/evidence_seeker_pipeline.py`) parses:
  - Interpretation: `interpretation_text`, `confirmation_level`, `average_confirmation` (confidence), `verbalized_confirmation` (summary), `raw` (full CheckedClaim).
  - Evidence (per interpretation, from `documents`): `text`, `uid` (chunk id), `metadata`, `score` from `confirmation_by_document[uid]`.
- Persisted DB (`backend/app/models/fact_check.py`):
  - `FactCheckResult.raw_payload` stores full interpretation dict (includes `confirmation_by_document`, `documents[].metadata`, `documents[].text` if present).
  - `FactCheckEvidence.metadata_payload` stores the document metadata (where wider excerpts likely live).
- Public API today (`frontend/src/types/public.ts`):
  - `results: FactCheckResult[]` with `evidence: FactCheckEvidence[] { evidenceText, chunkLabel, score, metadata? }`.
  - UI only renders chunk label/text/score; raw payload is not used.

## Required Payload for V2
Expose enough to render per-source context without extra calls. Two options—pick one and keep it consistent:
1) **Raw passthrough (preferred for speed)**: Add `rawPayload` to each `FactCheckResult` in the public run detail response (sanitized). This includes `confirmation_by_document`, `documents[].metadata`, `documents[].uid`, and (if present) `documents[].text`.
2) **Curated fields** (if raw is too permissive):
   - `result.confirmationByDocument: Record<string, float>`
   - `result.documents: { uid: string; metadata: Record<string, unknown>; text?: string }[]`
   - Keep `evidence` as is.

Notes on metadata/excerpts:
- Larger excerpt likely resides in `evidence.metadata.context` or similar; confirm via logging.
- If `documents[].text` is present, use as wider context fallback.
- Strip or whitelist sensitive metadata before exposing publicly.

## API Changes
- Backend serializer for public `GET /public/fact-checks/{uuid}`:
  - Include `raw_payload` or curated fields above.
  - Ensure `evidence.metadata_payload` is included in the `evidence` array (today it is already exposed as `metadata?`).
  - Document the keys used for wider context (e.g., `context`, `full_text`, `passage`).
- If adding fields, update `frontend/src/types/public.ts` and `frontend/src/types/factCheck.ts`.
- Keep `score` mapped from `confirmation_by_document` (already assigned in parser).

## Frontend Requirements (Public Fact Check Page)
- Interpretation card:
  - Show interpretation text, confirmation badge, confidence %, optional `summary`.
  - Add evidence count + top/avg score chip.
- Evidence section per interpretation:
  - Accordion titled “Sources (n)” collapsed by default; “Expand all/Collapse all” controls.
  - Each source card:
    - Header: document title/uid, optional link (if metadata has `url`), score badge, stance tag (supports/refutes/neutral—currently supports only).
    - Body (collapsed preview): 1–2 line snippet from `evidenceText`.
    - “Show full excerpt” expander reveals:
      - Full chunk text (`evidenceText` full).
      - Wider context: `evidence.metadata.context` (or confirmed key) or `documents[].text` fallback.
      - Confirmation score for this document (from `confirmation_by_document`).
      - Metadata tags (author/year/page/etc. from metadata).
    - “Open in reader” modal/drawer:
      - Full excerpt + metadata, next/prev source navigation.
- Global controls:
  - Sort sources: by score (default), by doc title, by returned order.
  - Filter chips (future): stance.
  - Loading/skeletons while polling; empty state if no evidence.

## Development Steps
1) **Inspect payload in dev** (temporary console logs in `PublicFactCheckPage`):
   - Log `result.rawPayload` if added; else log `evidence.metadata` to find context key.
   - Confirm mapping between `chunkLabel`/`uid` and `confirmation_by_document`.
2) **Backend update**:
   - Extend public serializer to include `raw_payload` or curated fields; sanitize/whitelist metadata.
   - If needed, copy wider excerpt into a stable key (e.g., `metadata.context`).
3) **Types**:
   - Update `FactCheckResult`/`FactCheckEvidence` types to include new fields (`rawPayload` or `documents`, `confirmationByDocument`).
4) **UI**:
   - Add `EvidenceAccordion` component with per-source cards and expanders.
   - Render score badge from `evidence.score`; show doc-level score from `confirmation_by_document` if present.
   - Use metadata/context for “full excerpt”; fallback to `evidenceText`.
   - Add expand-all/collapse-all, sort dropdown.
   - Remove dev logs after confirming data shape.

## Open Questions / Assumptions
- Exact key for wider context in metadata (`context`, `full_text`, `passage`?). Needs confirmation via logging or backend doc.
- Are document titles/links available in metadata? If not, can we enrich evidence payload with `document.title`/`url`?
- Any metadata that must not be exposed publicly (PII, internal IDs)? Decide whitelist vs. blacklist.

## Acceptance Criteria
- Public fact-check detail response contains the fields needed to render per-source excerpts and scores.
- Public fact-check page shows interpretations with collapsible “Sources (n)” sections.
- Each source shows snippet, expandable full excerpt/context, score, and metadata tags without overwhelming the default view.
- Progressive disclosure works on desktop and mobile; no large text walls on initial load.
