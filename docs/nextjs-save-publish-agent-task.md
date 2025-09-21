# Next.js Agent Task: Save & Publish Schedule (API v2)

This task equips the Next.js app with Save (assignments) and Publish flows for the admin schedule page, using API v2 endpoints.

## Scope
- Implement Save schedule changes via `POST /api/v2/admin/schedule/save`.
- Implement Publish current schedule via `POST /api/v2/admin/schedule/{schedule_id}/publish`.
- Wire UI buttons, loading/disabled states, optimistic updates, and error handling aligned with `docs/nextjs-api-error-handling.md`.

## Endpoints
- Save: `POST /api/v2/admin/schedule/save`
  - Body:
    ```json
    {
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "schedule_type": "helpdesk|lab",
      "assignments": [
        {
          "day": "Monday",
          "time": "9:00 am",
          "cell_id": "cell-0-0",
          "staff": [ { "id": "staff001", "name": "John Doe" } ]
        }
      ]
    }
    ```
  - Success (200): `{ success, data: { schedule_id, assignments_processed, start_date, end_date, errors? }, message }`
- Publish: `POST /api/v2/admin/schedule/{schedule_id}/publish`
  - Success (200): `{ success, data: { schedule_id, published_at, notifications_sent }, message }`

Notes:
- `schedule_id` can be obtained from Generate response or Current Schedule (`GET /api/v2/admin/schedule/current`).
- Admin role determines type; `schedule_type` can be omitted if role is correctly set server-side.

## Data Contract (Assignments)
- `day`: Display label (e.g., "Monday").
- `time`: Display label matching the grid’s slot (e.g., "9:00 am").
- `cell_id`: Stable UI identifier for the grid cell (optional server use; useful for reconciling responses to UI cells).
- `staff`: Array with at least `{ id: string; name: string }`. Keep IDs canonical (usernames/UUIDs).

## Implementation Tasks
1) API client auth header injection
- Ensure all protected calls attach `Authorization: Bearer <token>`.
- Option A: Enhance `lib/apiClient.ts` to inject token from a central store.
  ```ts
  // lib/authToken.ts
  let token: string | null = null;
  export const setToken = (t: string | null) => { token = t }; 
  export const getToken = () => token;
  ```
  ```ts
  // lib/apiClient.ts (augment headers)
  import { getToken } from './authToken';
  // ... inside apiFetch
  const auth = getToken();
  const headers = { 'Content-Type': 'application/json', ...(init?.headers || {}), ...(auth ? { Authorization: `Bearer ${auth}` } : {}) };
  const res = await fetch(input, { ...init, headers, credentials: 'include' });
  ```

2) Save action
- Build `saveSchedule(payload)` in `lib/scheduleApi.ts`.
- Gather payload from the grid state: `start_date`, `end_date`, `schedule_type`, `assignments`.
- Use optimistic UI: snapshot → optimistic apply → call API → success toast → keep; on failure → rollback and banner.

3) Publish action
- Build `publishSchedule(scheduleId)` in `lib/scheduleApi.ts`.
- Confirm via modal; disable during request; on success: toast + mark schedule as `published` in state.

4) UI Integration
- Add `Save` and `Publish` buttons to the admin schedule page toolbar.
- Disable `Save` when no changes; disable `Publish` when already published or while saving.
- Show an "Unpublished changes" banner when the working copy differs from the last saved snapshot.

5) Error handling
- 400/422: inline cell/row hints and a banner summary.
- 404 (publish): schedule not found → refresh/regen CTA.
- 409 (save/publish): conflict → prompt refresh and reconcile.
- 500+: banner with `Retry` and optional auto-retry for publish notification tasks.

## TypeScript: API layer
```ts
// lib/scheduleApi.ts
import { apiFetch } from './apiClient';

export type StaffRef = { id: string; name: string };
export type Assignment = { day: string; time: string; cell_id?: string; staff: StaffRef[] };

export type SavePayload = {
  start_date: string;
  end_date: string;
  schedule_type?: 'helpdesk' | 'lab';
  assignments: Assignment[];
};

export async function saveSchedule(payload: SavePayload) {
  return apiFetch<{ schedule_id: number; schedule_type: string; assignments_processed: number; start_date: string; end_date: string; errors?: unknown }>(
    '/api/v2/admin/schedule/save',
    { method: 'POST', body: JSON.stringify(payload) }
  );
}

export async function publishSchedule(scheduleId: number) {
  return apiFetch<{ schedule_id: number; published_at: string; notifications_sent: number }>(
    `/api/v2/admin/schedule/${scheduleId}/publish`,
    { method: 'POST' }
  );
}
```

## React integration snippets
```tsx
// app/admin/schedule/_actions.ts
import { saveSchedule, publishSchedule, SavePayload } from '@/lib/scheduleApi';
import { HttpError } from '@/lib/apiClient';

export async function handleSave(payload: SavePayload, { onSuccess, onError, rollback }: { onSuccess?: () => void; onError?: (m: string) => void; rollback?: () => void }) {
  try {
    const res = await saveSchedule(payload);
    // toast.success(res.message ?? 'Schedule saved');
    onSuccess?.();
    return res.data;
  } catch (e) {
    rollback?.();
    const msg = e instanceof HttpError ? e.message : 'Save failed.';
    onError?.(msg);
    throw e;
  }
}

export async function handlePublish(scheduleId: number, { onSuccess, onError }: { onSuccess?: () => void; onError?: (m: string) => void }) {
  try {
    const res = await publishSchedule(scheduleId);
    // toast.success(res.message ?? 'Schedule published');
    onSuccess?.();
    return res.data;
  } catch (e) {
    const msg = e instanceof HttpError ? e.message : 'Publish failed.';
    onError?.(msg);
    throw e;
  }
}
```

## Deliverables
- `lib/authToken.ts` (or equivalent) to store and retrieve JWT.
- `lib/scheduleApi.ts` with `saveSchedule` and `publishSchedule` functions.
- Admin schedule page wired buttons: Save + Publish with loading/disabled states.
- Optimistic UI for Save with rollback on error.
- Confirmation modal for Publish; success state updates.
- User feedback: toasts/banners/errors per `nextjs-api-error-handling.md`.

## Acceptance Criteria
- Save posts the correct payload, returns success toast, and updates UI without a full reload.
- Publish calls the endpoint with a valid `schedule_id`, shows success toast, and marks schedule as published.
- 401 results redirect to login preserving `returnTo`; 403 shows permission banner; 404 shows actionable empty state.
- 409 on Save triggers a refresh guidance banner; local changes are preserved for review.
- Loading/disabled states prevent duplicate submissions; keyboard and screen reader users can operate buttons.

## QA Checklist
- Save with valid payload → 200 success; verify `assignments_processed` matches expectation.
- Save with invalid dates → 400/422; inline field errors shown.
- Publish nonexistent schedule → 404; shows refresh/regen CTA.
- Rapid double-click on Publish → single request; second is ignored/disabled.
- Token missing/expired → 401 flow works end-to-end.

## Notes
- If you later switch to HttpOnly cookies for JWT, keep `credentials: 'include'` and remove header injection. Until then, ensure the `Authorization` header is present on every protected call.
- For lab schedules, slot sizes and validation differ; the payload shape remains the same from the UI perspective.
# Next.js Save & Publish Schedule — AI Agent Task Plan

This task adds Save and Publish capabilities to the Next.js admin schedule page using API v2. It assumes the Generate flow is implemented (see `docs/nextjs-generate-schedule-agent-task.md`).

## Overview
- Save: POST schedule assignments back to the server.
- Publish: Mark a schedule as active and notify staff.
- Provide clear UI feedback (success, errors) and optimistic updates where appropriate.

## Backend Contract (API v2)
- Base: `/api/v2`
- Auth: JWT cookie (`credentials: 'include'`).
- Envelope:
  - Success: `{ "success": true, "data": { ... }, "message"?: string }`
  - Error: `{ "success": false, "message": string, "errors"?: object }`

### Endpoints
- Save schedule changes:
  - `POST /admin/schedule/save`
  - Body:
    ```json
    {
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "assignments": [
        {
          "day": "Monday",
          "time": "9:00 am",
          "cell_id": "cell-0-0",
          "staff": [ { "id": "<staff_id>", "name": "<name>" } ]
        }
      ],
      "schedule_type": "helpdesk" | "lab"
    }
    ```
  - Response Data: `{ schedule_id: number, assignments_processed: number, errors?: array }`

- Publish schedule:
  - `POST /admin/schedule/<schedule_id>/publish`
  - Response Data: `{ schedule_id: number, published_at: string, notifications_sent: number }`

## Deliverables (Files/Changes)
- `components/ScheduleGrid.tsx` enhancements:
  - Accept `editable` flag and callbacks for local edits.
  - Expose a `toAssignments()` selector to produce the `assignments` array.
- `app/admin/schedule/page.tsx` changes:
  - Add Save and Publish buttons.
  - Implement `onSave()` to collect assignments and POST save.
  - Implement `onPublish()` to call publish with current `schedule_id`.
- Optional helpers:
  - `lib/scheduleAdapter.ts` to map UI state ↔ API `assignments` payload.

## Tasks
1) Extend grid for editing
- Within `ScheduleGrid`, render cells listing assistants and an Add/Remove affordance.
- Maintain local state of assignments (or lift state to page and pass down). 
- Provide a function/prop to serialize current UI into the `assignments` shape.
- Acceptance:
  - User can add/remove assistants in a cell (UI only for now).
  - `toAssignments()` returns all cells, including empty staff arrays.

2) Implement Save
- In the page component:
  - Keep `start_date`, `end_date`, and the last known `schedule_id` (from Generate).
  - On Save, build payload `{ start_date, end_date, assignments, schedule_type? }` and POST to `/api/v2/admin/schedule/save`.
  - Use optimistic update: show saving state; on error, show banner and rollback if you changed local state preemptively.
- Acceptance:
  - Successful save shows a toast and displays `assignments_processed` from response.
  - Server errors display a banner and do not clear unsaved changes indicator.

3) Implement Publish
- Require a valid `schedule_id` from the last Generate/Details response.
- POST to `/api/v2/admin/schedule/<id>/publish`.
- On success, show a toast and optionally mark the page as "Published" with timestamp.
- Acceptance:
  - Publish button disabled if no `schedule_id`.
  - On success, UI displays `published_at` and `notifications_sent`.

4) Error handling & UX
- Map 400/422 to inline form/cell errors; 401 → login; 403 → not allowed; 409 → conflict banner; 5xx → retry option.
- Reference `docs/nextjs-api-error-handling.md` for patterns.
- Acceptance:
  - Clear, accessible feedback on failure with retry.

## Sample Code Snippets

page.tsx (Save/Publish actions excerpt)
```tsx
import { apiFetch, HttpError } from '@/lib/apiClient';
import type { Schedule } from '@/types/schedule';

export default function AdminSchedulePage() {
  // ...existing state
  const [scheduleId, setScheduleId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);

  async function onSave(assignments: any[], scheduleType?: 'helpdesk'|'lab') {
    setSaving(true);
    try {
      const res = await apiFetch<{ schedule_id: number; assignments_processed: number }>(
        '/api/v2/admin/schedule/save',
        {
          method: 'POST',
          body: JSON.stringify({ start_date, end_date, assignments, schedule_type: scheduleType })
        }
      );
      setScheduleId(res.data.schedule_id);
      toast.success(res.message ?? `Saved ${res.data.assignments_processed} cells`);
    } catch (e) {
      banner.error(e instanceof HttpError ? e.message : 'Save failed');
    } finally { setSaving(false); }
  }

  async function onPublish() {
    if (!scheduleId) return;
    setPublishing(true);
    try {
      const res = await apiFetch<{ schedule_id: number; published_at: string; notifications_sent: number }>(
        `/api/v2/admin/schedule/${scheduleId}/publish`,
        { method: 'POST' }
      );
      toast.success(res.message ?? 'Schedule published');
      // Optionally show published_at in UI
    } catch (e) {
      banner.error(e instanceof HttpError ? e.message : 'Publish failed');
    } finally { setPublishing(false); }
  }

  return (
    // ...
    <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
      <button onClick={() => onSave(toAssignments(), inferredType)} disabled={saving || !schedule}> {saving ? 'Saving…' : 'Save'} </button>
      <button onClick={onPublish} disabled={publishing || !scheduleId}> {publishing ? 'Publishing…' : 'Publish'} </button>
    </div>
  );
}
```

scheduleAdapter.ts (example)
```ts
import type { Schedule } from '@/types/schedule';

export function scheduleToAssignments(schedule: Schedule) {
  const assignments: Array<{ day: string; time: string; cell_id: string; staff: Array<{ id: string; name: string }> }> = [];
  schedule.days.forEach((day, di) => {
    day.shifts.forEach((shift, ti) => {
      const cellId = `cell-${di}-${ti}`;
      assignments.push({ day: day.name, time: shift.time, cell_id: cellId, staff: shift.assistants || [] });
    });
  });
  return assignments;
}
```

## Acceptance Criteria (End-to-End)
- Save posts the full assignments matrix for the current date range and reports success; errors are visible and actionable.
- Publish is disabled until a schedule exists; on success, UI shows published status/time.
- All requests include cookies and adhere to the v2 envelope.

## Manual Test Steps
1. Generate a schedule (see generate task doc) and ensure a `schedule_id` is stored.
2. Make a few local edits (add/remove assistants) and click Save. Expect success toast, no crash, and validation feedback for any errors.
3. Click Publish. Expect success toast and a published timestamp to appear.

## References
- Generate flow: `docs/nextjs-generate-schedule-agent-task.md`
- Error handling: `docs/nextjs-api-error-handling.md`
- Backend endpoints: `App/views/api_v2/schedule.py`