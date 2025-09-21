# Next.js Generate Schedule Flow — AI Agent Task Plan

This task guides implementing the "Generate Schedule" flow in a Next.js admin page using the API v2 endpoints already available in the Flask backend. The goal: post a date range, fetch the generated schedule, and render it in a grid similar to the current Flask UI (helpdesk vs lab layouts).

## Overview
- Build a Next.js page with date inputs and a Generate button.
- Call API v2 to generate a schedule using only `start_date` and `end_date`.
- Fetch schedule details by `schedule_id` and render a grid.
- Provide loading, success, and error feedback.

## Backend Contract (API v2)
- Base: `/api/v2`
- Auth: JWT cookie; send requests with `credentials: 'include'`. If using header tokens, add `Authorization: Bearer <JWT>`.
- Envelope:
  - Success: `{ "success": true, "data": { ... }, "message"?: string }`
  - Error: `{ "success": false, "message": string, "errors"?: object }`
- Endpoints used:
  - Generate: `POST /admin/schedule/generate`
    - Body: `{ "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }`
    - Response Data: `{ schedule_id: number, schedule_type: "helpdesk"|"lab" }`
  - Details: `GET /admin/schedule/details?id=<schedule_id>`
    - Response Data: `{ schedule: { days: Day[] } }`
- Data shape to render (typical):
  - `Day`: `{ name: string, shifts: Shift[] }`
  - `Shift`: `{ time: string, assistants: Assistant[] }`
  - `Assistant`: `{ id: string, name: string }`

## Deliverables (Files to Create)
- `lib/apiClient.ts`: Fetch wrapper returning typed API v2 envelopes with `credentials: 'include'`.
- `app/admin/schedule/page.tsx` (App Router) or `pages/admin/schedule.tsx` (Pages Router): UI with date pickers, Generate button, and grid render.
- `components/ScheduleGrid.tsx`: Pure presentational grid renderer.
- `types/schedule.ts`: TS interfaces for `Day`, `Shift`, `Assistant`, `Schedule`.
- Optional: `components/Banner.tsx`, `components/Toast.tsx` for feedback.

## Tasks
1) API client scaffold
- Create `lib/apiClient.ts` with:
  - `ApiSuccess<T>` / `ApiError` types.
  - `HttpError` class (status + body).
  - `apiFetch<T>(url, init)`: sets `Content-Type`, `credentials: 'include'`, parses JSON, throws `HttpError` on non-OK or `{ success: false }`.
- Acceptance:
  - Handles JSON/non-JSON responses safely.
  - Maps common HTTP statuses to friendly messages (see docs/nextjs-api-error-handling.md).

2) Schedule page UI
- Add page with:
  - Two `<input type="date" />` fields: `start_date`, `end_date`.
  - `Generate` button (disabled if dates missing; shows spinner when loading).
  - Area for error banner, success toast, and empty state.
- Acceptance:
  - Button enabled only when both dates provided.
  - Shows loading state while requests in flight.

3) Generate action
- Implement `onGenerate()`:
  - `POST /api/v2/admin/schedule/generate` with `{ start_date, end_date }`.
  - On success, read `data.schedule_id`.
  - `GET /api/v2/admin/schedule/details?id=<schedule_id>`.
  - Store `schedule` in state; clear errors; show success toast.
  - On failure, show banner error and keep previous state.
- Acceptance:
  - Sends only `start_date` and `end_date`.
  - Handles v2 envelope correctly (uses `data.*`).

4) Grid rendering
- Create `components/ScheduleGrid.tsx` that renders a table:
  - Columns: one per day (`schedule.days`). First column is time label.
  - Rows: all distinct time slots across the week (from `day.shifts[].time`).
  - Cells: list assistant names for that day/time; show em-dash when empty.
- Acceptance:
  - Works for both helpdesk and lab data shapes.
  - No layout shift on empty slots; scrolls horizontally if needed.

5) Layout presets (Helpdesk vs Lab)
- If `schedule_type` is needed, infer from generate response or simply render based on provided `schedule.days`:
  - Helpdesk: Mon–Fri; time slots like `9:00 am` → `4:00 pm` (8 hourly slots).
  - Lab: Mon–Sat; time blocks: `8:00 am - 12:00 pm`, `12:00 pm - 4:00 pm`, `4:00 pm - 8:00 pm`.
- Acceptance:
  - Grid renders correctly with either slot pattern if present.

6) Feedback & errors
- On success: short-lived toast (e.g., "Schedule generated").
- On error: persistent banner (e.g., validation 400/422 vs server 5xx); friendly copy.
- Use `docs/nextjs-api-error-handling.md` guidance for mapping statuses.
- Acceptance:
  - User-visible feedback for both success and failure.

7) Auth plumbing
- Ensure requests include cookies: `credentials: 'include'`.
- If project uses header tokens, support injecting `Authorization` via a helper.
- Acceptance:
  - Generation works when signed in; redirects on 401 handled by app-wide logic if present.

## Sample Code Snippets

lib/apiClient.ts
```ts
export type ApiSuccess<T> = { success: true; data: T; message?: string };
export type ApiError = { success: false; message: string; errors?: Record<string, unknown> };

export class HttpError extends Error {
  constructor(public status: number, message: string, public body?: unknown) { super(message); }
}

export async function apiFetch<T>(url: string, init?: RequestInit): Promise<ApiSuccess<T>> {
  const res = await fetch(url, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    credentials: 'include',
  });
  const isJson = res.headers.get('content-type')?.includes('application/json');
  const body = isJson ? await res.json().catch(() => ({})) : {};
  if (!res.ok || (body as any)?.success === false) {
    const msg = (body as any)?.message || 'Request failed';
    throw new HttpError(res.status, msg, body);
  }
  return body as ApiSuccess<T>;
}
```

app/admin/schedule/page.tsx
```tsx
'use client';
import { useState } from 'react';
import { apiFetch, HttpError } from '@/lib/apiClient';

type Assistant = { id: string; name: string };
type Shift = { time: string; assistants: Assistant[] };
type Day = { name: string; shifts: Shift[] };
type Schedule = { days: Day[] };

export default function AdminSchedulePage() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [schedule, setSchedule] = useState<Schedule | null>(null);

  async function onGenerate() {
    setError(null); setLoading(true);
    try {
      const gen = await apiFetch<{ schedule_id: number; schedule_type: 'helpdesk'|'lab' }>(
        '/api/v2/admin/schedule/generate',
        { method: 'POST', body: JSON.stringify({ start_date: startDate, end_date: endDate }) }
      );
      const id = gen.data.schedule_id;
      const details = await apiFetch<{ schedule: Schedule }>(`/api/v2/admin/schedule/details?id=${id}`);
      setSchedule(details.data.schedule);
    } catch (e) {
      setError(e instanceof HttpError ? e.message : 'Failed to generate schedule');
    } finally { setLoading(false); }
  }

  return (
    <div>
      <h1>Admin Schedule</h1>
      <div style={{ display: 'flex', gap: 8 }}>
        <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
        <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
        <button onClick={onGenerate} disabled={loading || !startDate || !endDate}>
          {loading ? 'Generating…' : 'Generate'}
        </button>
      </div>
      {error && <div role="alert" style={{ marginTop: 12, color: '#b00' }}>{error}</div>}
      {schedule ? <ScheduleGrid schedule={schedule} /> : <div style={{ marginTop: 16 }}>Pick dates and click Generate.</div>}
    </div>
  );
}

function ScheduleGrid({ schedule }: { schedule: Schedule }) {
  const times = Array.from(new Set(schedule.days.flatMap(d => d.shifts.map(s => s.time))));
  return (
    <div style={{ marginTop: 16, overflowX: 'auto' }}>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            {schedule.days.map(d => <th key={d.name}>{d.name}</th>)}
          </tr>
        </thead>
        <tbody>
          {times.map(time => (
            <tr key={time}>
              <td>{time}</td>
              {schedule.days.map(d => {
                const shift = d.shifts.find(s => s.time === time);
                return (
                  <td key={d.name + time}>
                    {shift?.assistants?.length ? shift.assistants.map(a => <div key={a.id}>{a.name}</div>) : <span style={{ color: '#888' }}>—</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

## Acceptance Criteria (End-to-End)
- Enter a valid date range and click Generate → POST to v2 (with cookie) and then GET details; page shows a table with days as columns and times as rows.
- Shows a visible loading state while requests are running.
- On success, shows a brief success toast (or simple message) and renders the schedule.
- On error, shows a banner with a helpful message; no crash.
- Works for both helpdesk and lab schedule shapes without code changes.

## Manual Test Steps
1. Sign in as an admin (to get a valid JWT cookie).
2. Navigate to the Next.js admin schedule page.
3. Select a Monday–Friday (helpdesk) or Monday–Saturday (lab) range.
4. Click Generate. Expect loading → success toast → grid rendered.
5. Hard refresh and ensure state can be reloaded by re-generating if needed.

## References
- API behavior and error handling: `docs/nextjs-api-error-handling.md`
- Backend endpoints: `App/views/api_v2/schedule.py` (url prefix `/api/v2`)
