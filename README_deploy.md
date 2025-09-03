# Deployment Notes

This project separates full development dependencies from the lightweight production set required for Vercel serverless.

## Files
- `requirements.full.txt`: Original full dependency list (includes heavy libs: ortools, WeasyPrint, gevent, locust, pytest, Flask-Admin, gunicorn).
- `requirements.txt`: Trimmed list for serverless deployment. Excludes heavy / optional packages.
- `.vercelignore`: Excludes large or unnecessary data (sample CSVs, images, instance DB, tests, etc.) so the unzipped function size stays under 250 MB.

## Why Trim?
Vercel Python serverless functions must be < 250 MB unzipped. Heavy native wheels (ortools, WeasyPrint + Cairo/Pango stack, locust, gevent) easily push the bundle over the limit even if rarely used.

## Removed / Deferred Features in Serverless Build
| Feature | Library | Result in Trimmed Build |
|---------|---------|-------------------------|
| Scheduling optimization | ortools | Endpoints depending on optimization will return an error message (guard in code) |
| PDF export | WeasyPrint | PDF generation endpoints raise runtime error (guard) |
| Load testing | locust | Not available in prod; run locally with full requirements |
| Greenlet async worker tuning | gevent/gunicorn | Not needed for Vercel's managed runtime |
| CLI testing via `pytest` | pytest | Use locally only |

## Local Development (Full Feature Set)
```bash
# (Windows PowerShell examples)
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.full.txt
flask --app wsgi.py run
```

## Local Dev (Mimic Production Slim Build)
```bash
python -m venv .venv-slim; .\.venv-slim\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app wsgi.py run
```
Expect scheduling/PDF endpoints to respond with graceful error messages in slim mode.

## Restoring a Feature to Production
1. Add the needed package back to `requirements.txt` (only if absolutely required at runtime).
2. Ensure `.vercelignore` does not exclude assets required for that feature.
3. Redeploy and confirm the unzipped size remains < 250 MB.

## Alternative for Heavy Features
- Host a separate microservice (Render / Railway / Fly.io) running the full stack (can use `Dockerfile`).
- Expose optimization or PDF generation as an internal API the Vercel app calls asynchronously.

## Troubleshooting
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| 500 with message about scheduling engine | `ortools` excluded | Use full environment or deploy aux service |
| 500 PDF generation error | `WeasyPrint` excluded | Same as above |
| ImportError for a removed lib | Code path executed before guard | Add lazy import or conditional similar to existing guards |

## Deployment Steps (Vercel)
1. Commit changes: trimmed `requirements.txt`, added `.vercelignore`, lazy import guards.
2. Push to main (or branch) and let Vercel build.
3. Verify health endpoint: `/healthcheck`.
4. Exercise primary CRUD/auth flows.

## Keeping Things Clean
- Add any new large sample/data/test directories to `.vercelignore`.
- Avoid adding heavy scientific/optimization libs unless isolated.

---
Generated to document the serverless optimization approach.
