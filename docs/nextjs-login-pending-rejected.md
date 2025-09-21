# Next.js Login Handling — Pending/Rejected Registrations (API v2)

Backend v2 login now differentiates between invalid credentials and registration states using HTTP codes and `errors.code` in the envelope.

## Contract
- Endpoint: `POST /api/v2/auth/login`
- Success (200): `{ success: true, data: { user: {...}, token: string }, message: 'Login successful' }`
- Errors:
  - 401 `{ success: false, message: 'Invalid username or password', errors: { code: 'INVALID_CREDENTIALS' } }`
  - 403 Pending `{ success: false, message: 'Your registration request is pending review.', errors: { code: 'REG_PENDING', requested_at?: ISO } }`
  - 403 Rejected `{ success: false, message: 'Your registration request was rejected.', errors: { code: 'REG_REJECTED', reviewed_at?: ISO, reviewed_by?: string } }`
  - 403 Approved but not provisioned `{ success: false, message: 'Your registration is approved but your account is not yet provisioned...', errors: { code: 'REG_APPROVED_NOT_PROVISIONED' } }`

## UI Behavior
- `REG_PENDING`:
  - Show banner: "Your registration is pending review. You’ll be notified once approved."
  - Offer link: "Contact admin" or "Learn more".
- `REG_REJECTED`:
  - Show banner: "Your registration was rejected."
  - Offer CTA: "Resubmit" or link to support.
- `REG_APPROVED_NOT_PROVISIONED`:
  - Show banner: "Approved, provisioning in progress. Try again later."
- `INVALID_CREDENTIALS` (401):
  - Show inline error on fields: "Invalid username or password."

## Client Code (excerpt)
```ts
import { apiFetch, HttpError } from '@/lib/apiClient';

async function login(username: string, password: string) {
  try {
    const res = await apiFetch<{ user: any; token: string }>(
      '/api/v2/auth/login',
      { method: 'POST', body: JSON.stringify({ username, password }) }
    );
    // Store token and redirect
    setToken(res.data.token);
    router.push('/admin');
  } catch (e) {
    if (e instanceof HttpError) {
      const code = (e.body as any)?.errors?.code;
      switch (code) {
        case 'REG_PENDING':
          showBanner('Your registration is pending review. You’ll be notified once approved.');
          break;
        case 'REG_REJECTED':
          showBanner('Your registration was rejected. Contact support if you think this is a mistake.');
          break;
        case 'REG_APPROVED_NOT_PROVISIONED':
          showBanner('Approved, provisioning in progress. Please try again shortly.');
          break;
        default:
          if (e.status === 401) setFieldError('password', 'Invalid username or password');
          else showBanner(e.message || 'Login failed');
      }
    } else {
      showBanner('Network error. Please try again.');
    }
  }
}
```

## Notes
- Keep using header-based JWT for now: attach `Authorization: Bearer <token>` to protected requests.
- If you later switch to HttpOnly cookies, ensure CORS and `credentials: 'include'` are configured.
- Show only one prominent banner at a time; keep it accessible with `role="alert"`.
