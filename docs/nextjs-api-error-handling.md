# Next.js UX Patterns for API v2 Responses

This guide documents the API v2 response shapes and how a Next.js frontend should handle them to deliver clear, actionable UI/UX – not generic "500 Internal Server Error" messages.

## 1) API v2 Envelope & Conventions

- Success response:
```json
{
  "success": true,
  "data": { /* payload */ },
  "message": "Optional human‑readable message"
}
```
- Error response:
```json
{
  "success": false,
  "message": "Primary error message",
  "errors": { /* field or detail map (optional) */ }
}
```
- Transport: HTTP status codes still matter. Always branch on `res.ok` first, then parse body.

## 2) HTTP Status → UX Strategy

Use friendly, context‑specific UI. Never surface raw codes to users.

- 200/201 OK/Created:
  - UI: success toast/banner with the API `message` where helpful.
  - Example: "Schedule generated successfully" → Show toast; update table.

- 202 Accepted (rare):
  - UI: show non‑blocking spinner/"working" banner with polling; allow cancel.

- 204 No Content:
  - UI: silent success; if action implies change (e.g., delete), optimistically update UI.

- 400 Bad Request (validation/user errors):
  - UI: inline field errors using `errors` map; summary banner at top.
  - CTA: keep focus on first invalid field; provide helpful hints.

- 401 Unauthorized (missing/expired JWT):
  - UI: redirect to login with a preserved `returnTo` query; show "Session expired" toast.
  - Action: clear auth store; refresh CSRF/JWT if using silent refresh.

- 403 Forbidden (role/permission):
  - UI: friendly "Not allowed" state with contact/admin CTA.
  - Optional: hide or disable restricted actions proactively based on role.

- 404 Not Found:
  - UI: contextual empty state. Example: "No current schedule found for this week." with a "Generate" button.

- 409 Conflict (duplication/state race):
  - UI: prompt to refresh and reconcile; show diff if applicable.
  - Example: assignment already exists → "Already assigned" inline tag.

- 422 Unprocessable Entity (semantic validation):
  - UI: similar to 400 but emphasize business rule hints (availability, capacity).

- 429 Too Many Requests:
  - UI: soft warning toast; backoff/retry with progress indicator.

- 500/502/503/504 Server/Network errors:
  - UI: friendly banner + retry button; auto‑retry with exponential backoff and cap.
  - Diagnostics: optionally include correlation ID from `X-Request-Id` if present.

## 3) Frontend Fetch Layer (Recommended)

Create a single client that normalizes responses and raises typed errors. This keeps pages/components lean and consistent.

```ts
// lib/apiClient.ts
export type ApiSuccess<T> = { success: true; data: T; message?: string };
export type ApiError = { success: false; message: string; errors?: Record<string, unknown> };

export class HttpError extends Error {
  status: number;
  body?: ApiError | unknown;
  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

export async function apiFetch<T>(input: RequestInfo, init?: RequestInit): Promise<ApiSuccess<T>> {
  const res = await fetch(input, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {})
    },
    credentials: 'include',
  });

  let body: unknown = undefined;
  const isJson = res.headers.get('content-type')?.includes('application/json');
  if (isJson) {
    body = await res.json().catch(() => undefined);
  }

  if (!res.ok) {
    const msg = (body as ApiError)?.message || defaultMessageForStatus(res.status);
    throw new HttpError(res.status, msg, body);
  }

  return (body || { success: true, data: {} }) as ApiSuccess<T>;
}

function defaultMessageForStatus(status: number): string {
  switch (status) {
    case 400: return 'Please fix the highlighted fields and try again.';
    case 401: return 'Your session expired. Please sign in again.';
    case 403: return 'You do not have permission to perform this action.';
    case 404: return 'We couldn’t find what you’re looking for.';
    case 409: return 'That action conflicts with the current state.';
    case 422: return 'Please review the inputs and business rules.';
    case 429: return 'You’re making requests too quickly. Please wait a moment.';
    case 500: return 'Something went wrong on our side. Please try again.';
    case 502:
    case 503:
    case 504: return 'Service is temporarily unavailable. Retrying may help.';
    default: return 'Unexpected error occurred.';
  }
}
```

## 4) UI Patterns by Context

- Inline field errors (forms):
  - Render `errors` map near inputs; mark invalid with aria-invalid.
  - Scroll to first error; focus management for accessibility.

- Toasts and banners:
  - Success: short‑lived toast (3–5s).
  - Warning: longer banner with guidance.
  - Error: persistent banner with “Retry”/“Details”.

- Empty and error states:
  - Use action‑oriented empty states with primary CTA (e.g., Generate Schedule).
  - Provide secondary help link to docs/support where appropriate.

- Optimistic updates and rollback:
  - For quick actions (assign/remove staff), optimistically update UI.
  - If API fails, rollback state and show contextual error near the item.

## 5) Concrete Examples (Schedule Page)

### A) Generate Schedule
```ts
try {
  const res = await apiFetch<{ schedule_id: number }>(`/api/v2/admin/schedule/generate`, {
    method: 'POST',
    body: JSON.stringify({ start_date, end_date })
  });
  toast.success(res.message ?? 'Schedule generated');
  refreshSchedule(res.data.schedule_id);
} catch (e) {
  if (e instanceof HttpError) {
    if (e.status === 422 || e.status === 400) {
      banner.warn(e.message);
    } else if (e.status >= 500) {
      banner.error('Could not generate schedule. Retrying…');
      retryWithBackoff(() => /* re‑call */);
    }
  } else {
    banner.error('Network error. Check your connection.');
  }
}
```

### B) Save Assignments (Inline Rollback)
```ts
const prev = snapshot(assignments);
optimisticUpdate(assignments);
try {
  const res = await apiFetch(`/api/v2/admin/schedule/save`, {
    method: 'POST',
    body: JSON.stringify(payload)
  });
  toast.success(res.message ?? 'Schedule saved');
} catch (e) {
  restore(prev);
  if (e instanceof HttpError && e.status === 409) {
    banner.warn('Someone else changed this schedule. Please refresh.');
  } else {
    banner.error(e instanceof HttpError ? e.message : 'Save failed.');
  }
}
```

### C) Staff Availability (Batch)
```ts
try {
  const { data } = await apiFetch<{ results: Array<{ staff_id: string; day: string; time: string; is_available: boolean }>}>(
    `/api/v2/admin/schedule/staff/check-availability/batch`,
    { method: 'POST', body: JSON.stringify({ queries }) }
  );
  highlightCells(data.results);
} catch (e) {
  banner.error('Could not load availability. Cells will remain droppable.');
}
```

## 6) Components: Reusable UX Blocks

- `<FormErrorSummary />` – Renders API `errors` map; links to fields.
- `<Banner type="error|warning|success" />` – Persistent, actionable feedback.
- `<Toast />` – Short‑lived confirmations.
- `<RetryButton onRetry={fn} />` – Encapsulates backoff + disabled states.
- `<EmptyState title actionLabel onAction />` – For 404/empty data.

## 7) Retry & Backoff Utility

```ts
export async function retryWithBackoff<T>(fn: () => Promise<T>, attempts = 3, base = 400): Promise<T> {
  let lastErr: unknown;
  for (let i = 0; i < attempts; i++) {
    try { return await fn(); } catch (err) {
      lastErr = err;
      await new Promise(r => setTimeout(r, base * 2 ** i));
    }
  }
  throw lastErr;
}
```

## 8) Accessibility & Internationalization

- All banners/toasts support `role="status"`/`role="alert"`.
- Error copy is plain‑language and translatable.
- Focus moves to the most relevant element after actions/errors.

## 9) Observability Hooks (Optional)

- Read `X-Request-Id` from response headers; include in error telemetry.
- Log `HttpError.status`/`message` to monitoring (Sentry, etc.).
- Feature‑flag advanced retries for heavy operations.

## 10) Quick Checklist

- [ ] Centralized api calls with typed errors
- [ ] Map HTTP → friendly copy
- [ ] Inline field errors for 400/422
- [ ] Auth fallback for 401 + redirect with `returnTo`
- [ ] Permission handling for 403
- [ ] Empty states for 404
- [ ] Conflict handling for 409 (refresh guidance)
- [ ] Backoff for 5xx/429
- [ ] Optimistic UI + rollback
- [ ] Accessible banners/toasts and focus management
