# Next.js Login + Dashboard (Admin & Student) – Implementation Plan

This document analyzes the existing Flask UI for login and dashboards, clarifies the API v2 endpoints to consume from a Next.js app, and provides a step-by-step task list suitable for an AI agent to implement.

## What Exists In Flask (Reference)

- Login page: `App/templates/auth/login.html` + CSS `App/static/css/auth/login.css` + JS `App/static/js/auth/login.js`.
  - Posts to server-rendered route `/login` with form fields: `username` (ID) and `password`.
  - Client-side: minimal validation and flash-message handling.
  - Design: two-column layout (left image + title, right form), modern styles (no external UI library).
- Student dashboard (aka volunteer):
  - Template `App/templates/volunteer/dashboard/dashboard.html`
  - Base `App/templates/volunteer/base.html` extends shared nav and styling.
  - JS `App/static/js/volunteer/dashboard.js` adds simple hover/placeholder timers.
  - Data passed from server uses controller `get_dashboard_data(username)` in `App/views/volunteer.py`.
- Admin dashboard:
  - No dedicated server-rendered dashboard template found; Admin sections exist under `App/templates/admin/*` for schedule/requests/tracking but the API v2 provides a JSON dashboard at `/api/v2/admin/dashboard`.

## API v2 You Will Use From Next.js

- `POST /api/v2/auth/login` – returns `{ success, data: { user, token }, message }`.
- `POST /api/v2/auth/register` – multipart/form-data with required files; returns success message (used for onboarding, not login/dashboard).
- `POST /api/v2/auth/logout` – JWT required; client should just delete token.
- `GET /api/v2/me` – returns current user profile; requires `Authorization: Bearer <token>`.
- `GET /api/v2/admin/dashboard` – admin-only summary: schedules, pending items, attendance.
- `GET /api/v2/admin/stats` – admin-only detailed stats.
- `GET /api/v2/student/dashboard` – student-only: upcoming shifts, recent time entries, small stats.
- `GET /api/v2/student/schedule?start_date&end_date` – student schedule.

Response envelope is standardized via `App/views/api_v2/utils.py`:
- Success: `{ success: true, data: {...}, message? }`
- Error: `{ success: false, message, errors? }`

## Libraries/Packages Used In Flask UI

- No UI component library for login/dashboard. Pure HTML/CSS/vanilla JS.
- Icons via Google Material Icons CDN in `shared/base.html`.
- Notifications and layout helpers are custom files in `App/static/js` and `App/static/css`.
- Therefore, in Next.js you can:
  - Recreate styles directly (copy/port CSS rules) or
  - Use a UI library (e.g., Tailwind CSS, Chakra UI, Material UI) for faster build while matching look-and-feel.

## Recommended Next.js Stack

- Next.js 14+ with App Router.
- Tailwind CSS for quick styling parity with room for creative improvements.
- `next-safe-action` or your preferred fetch wrapper for typed server actions (optional).
- `zustand` or React Context for auth state; or store token in `HttpOnly` cookie via Next.js Route Handlers.
- `react-hook-form` + `zod` for the login form validation.

## Auth Decisions (Important)

- Backend expects JWT in `Authorization: Bearer <token>`.
- On login success, store token either:
  1) In memory + `localStorage` (simple, but less secure), or
  2) In an `HttpOnly` secure cookie set by a Next.js Route Handler (recommended).
- For SSR pages, prefer cookie-based so server can fetch with token.

## Data Mapping For UI

- Login page fields: `username`, `password`. Errors from API -> surface as inline errors and toasts.
- Student dashboard widgets:
  - Next shift: derive from the first item of `data.upcoming_shifts` and compute humanized time.
  - My Schedule: list of upcoming shifts, display date `YYYY-MM-DD` and time range `start_time–end_time`.
  - Full schedule grid: currently server-rendered in Flask; in Next.js fetch `/api/v2/student/schedule` and build a weekly grid.
- Admin dashboard widgets:
  - Quick stats: `published_count`, `pending_approvals`, `attendance_rate`.
  - Current schedule card: `data.schedules.current_schedule` if present.
  - Pending items: counts of registrations and requests.

## Page Layout Parity

- Keep two-column login layout and general dashboard card/sectioning.
- Use Material Icons (same CDN) or `@mui/icons-material`.
- Responsive behavior: mirror CSS breakpoints; Tailwind makes this straightforward.

## Improvements You Can Add

- Remember-me option storing token in cookie with configurable TTL.
- Error boundaries and skeleton loaders for dashboards.
- Role-based route guards and conditional navigation.
- Timezone awareness; use dayjs for date handling.
- Accessibility improvements: labels, focus styles, aria-live for errors.

## Implementation Tasks (AI Agent Checklist)

1. Scaffold project
   - Create a Next.js 14 app with App Router and Tailwind CSS.
   - Add deps: `zod`, `react-hook-form`, `zustand` (or Context), `dayjs`.

2. Auth store and utilities
   - Create `lib/api.ts` with a `fetchJson` wrapper handling base URL, JSON parsing, and error mapping to `{ success, message }`.
   - Create `lib/auth.ts` for token management (read/write token to cookie via server route `/api/session`).
   - Implement Next.js Route Handlers:
     - `POST /api/session` that proxies to Flask `POST /api/v2/auth/login`, stores token in `HttpOnly` cookie, returns user payload.
     - `DELETE /api/session` that clears cookie (logout) and optionally calls Flask `/auth/logout`.

3. Login page
   - Route: `/login` (app router page).
   - UI: replicate two-column layout; port styles from `login.css` to Tailwind (or a CSS Module).
   - Form: `username`, `password` with client validation; submit to `/api/session`.
   - On success: redirect to `/admin` or `/student` based on `data.user.is_admin`.

4. Global layout and nav
   - Create `app/(authed)/layout.tsx` with navbar containing links similar to Flask `shared/base.html`.
   - Implement server `getUser()` that reads token from cookie and calls `GET /api/v2/me` to render user-specific nav.
   - Add a Sign Out button calling `DELETE /api/session` then redirect to `/login`.

5. Student dashboard page
   - Route: `/student` (protected).
   - Server component loads:
     - `GET /api/v2/student/dashboard` for summary tiles and lists.
     - `GET /api/v2/student/schedule` for grid; build a weekly table with time slots and days.
   - Client widgets for hover effects and “starts in X” calculation using dayjs.

6. Admin dashboard page
   - Route: `/admin` (protected).
   - Server component loads:
     - `GET /api/v2/admin/dashboard` for top-line stats and current schedule card.
     - Optionally call `/api/v2/admin/stats` for extra charts/tables.

7. Route guards
   - Middleware: check cookie for token; if absent and route requires auth, redirect to `/login`.
   - Also enforce role segment: `/admin` requires `is_admin===true`; `/student` requires `is_admin===false`.

8. Error and loading states
   - Create `<LoadingCard />` skeletons; show toast errors on fetch failures.
   - Normalize API error format: read `message` from `{ success:false }`.

9. Theming and icons
   - Install Material Icons via `<link>` in `app/layout.tsx` head to match Flask.
   - Apply Tailwind colors to approximate the existing palette (`#0066cc`, etc.).

10. Tests and manual verification
   - Add simple Playwright tests for login redirect and guarding.
   - Provide `.env.local` with `NEXT_PUBLIC_API_BASE` pointing to Flask (e.g., `http://localhost:8080`).

## Example Snippets

- Route Handler: `POST /api/session` (proxy login)
```ts
// app/api/session/route.ts
import { cookies } from 'next/headers'

export async function POST(req: Request) {
  const body = await req.json()
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/api/v2/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  })
  const json = await res.json()
  if (!json.success) {
    return new Response(JSON.stringify(json), { status: res.status })
  }
  const token = json.data.token
  cookies().set('auth_token', token, { httpOnly: true, sameSite: 'lax', secure: process.env.NODE_ENV==='production' })
  return Response.json({ user: json.data.user })
}

export async function DELETE() {
  cookies().delete('auth_token')
  return Response.json({ success: true })
}
```

- Server helper to call API with token
```ts
// lib/api.ts
export async function apiGet(path: string, init?: RequestInit) {
  const token = (await import('next/headers')).cookies().get('auth_token')?.value
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.headers || {}),
      Authorization: `Bearer ${token}`,
    },
    cache: 'no-store'
  })
  const json = await res.json()
  if (!res.ok || !json.success) throw new Error(json.message || 'Request failed')
  return json.data
}
```

- Client login form using RHF + zod (pseudo)
```tsx
// app/login/page.tsx
'use client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'

const schema = z.object({ username: z.string().min(1), password: z.string().min(1) })

type Form = z.infer<typeof schema>

export default function Login() {
  const router = useRouter()
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Form>({ resolver: zodResolver(schema) })

  async function onSubmit(values: Form) {
    const res = await fetch('/api/session', { method: 'POST', headers: { 'Content-Type':'application/json' }, body: JSON.stringify(values) })
    const json = await res.json()
    if (!res.ok) { alert(json.message || 'Login failed'); return }
    if (json.user?.is_admin) router.replace('/admin'); else router.replace('/student')
  }

  return (
    <div className="grid md:grid-cols-2 min-h-screen">
      {/* Left column: title + image */}
      <div className="bg-[#0066cc] text-white p-8 flex flex-col justify-center">
        <h1 className="text-3xl font-bold mb-4">Help Desk Rostering System</h1>
        {/* optionally include image */}
      </div>
      {/* Right column: form */}
      <div className="flex items-center justify-center p-6 bg-slate-50">
        <form onSubmit={handleSubmit(onSubmit)} className="bg-white p-8 rounded-xl shadow w-full max-w-md space-y-4">
          <h2 className="text-2xl font-bold text-slate-800 text-center">Welcome Back</h2>
          <div>
            <label className="block text-slate-700 mb-1">ID Number</label>
            <input className="w-full border rounded px-3 py-2" {...register('username')} />
            {errors.username && <p className="text-red-600 text-sm">{errors.username.message}</p>}
          </div>
          <div>
            <label className="block text-slate-700 mb-1">Password</label>
            <input type="password" className="w-full border rounded px-3 py-2" {...register('password')} />
            {errors.password && <p className="text-red-600 text-sm">{errors.password.message}</p>}
          </div>
          <button disabled={isSubmitting} className="w-full bg-[#0066cc] hover:bg-[#0052a3] text-white rounded py-2">Sign In</button>
        </form>
      </div>
    </div>
  )
}
```

## Environment and Run

- Ensure Flask is running locally on `http://localhost:8080` with API v2 registered.
- Next.js `.env.local`:
```
NEXT_PUBLIC_API_BASE=http://localhost:8080
```

## Minimal Manual Test Flow

1. Load `/login`, submit admin creds from README or seeded data.
2. Verify redirect to `/admin` and dashboard tiles show counts.
3. Logout; login as student; verify `/student` shows upcoming shifts and schedule grid.
4. Try hitting a protected route without token; ensure middleware redirects to `/login`.

---

If you want, I can scaffold a minimal Next.js app folder with the outlined handlers and pages to jumpstart implementation.