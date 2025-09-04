# Registration & Approval Workflow Fix

## Overview
A series of foreign key and duplicate key errors occurred during the Help Desk Assistant registration and admin approval flow. These were caused by inserting related records (availability, assistant, user) out of the correct dependency order and by duplicating persistence of polymorphic models. The workflow is now stable and idempotent.

---
## Problems Encountered

### 1. Availability FK Violation During Registration
**Error:** `availability.username` FK to `student.username` failed.

**Cause:** Availability rows were created immediately after a registration form submission, but no `Student` (or `User`) row exists yet because the request is still pending approval.

**Fix:** Added a staging model `RegistrationAvailability` and deferred creation of real `Availability` rows until after approval (when the `Student` exists).

### 2. Availability FK Violation During Approval
**Error:** Still saw FK errors when approving after first fix.

**Cause:** Availability was created *before* committing the `Student` insert. Even though objects were added to the session, the FK constraint in PostgreSQL requires the referenced row to be physically persisted.

**Fix:** Split approval into two phases:
1. Commit core entities (`Student`, `HelpDeskAssistant`, etc.).
2. Then migrate staged availability into the `availability` table.

### 3. Duplicate Key on `users` Table
**Error:** `duplicate key value violates unique constraint "users_pkey"`.

**Cause:** The approval logic explicitly created a `User` instance *and* a `Student` instance. Since `Student` inherits from `User` (joined-table / single-table polymorphism via `polymorphic_on`), constructing both caused two inserts with the same primary key.

**Fix:** Removed explicit `User` creation; only create `Student`. Its constructor inserts the base `users` row and the subclass row correctly.

---
## Key Changes Implemented
| Area | Change |
|------|--------|
| Model | Added `RegistrationAvailability` to stage availability slots pre-approval. |
| Registration Controller | `create_registration_request` now stores availability in staging table instead of `availability`. |
| Approval Flow | Rewritten: create & flush `Student` first, then `HelpDeskAssistant`, then commit, then migrate availability. Removed redundant `User` creation. |
| Capabilities | Course capabilities added after assistant creation without intermediate commits. |
| Availability Migration | Performed only after successful core commit to guarantee FK integrity. |

---
## Updated Approval Sequence
1. Fetch pending `RegistrationRequest`.
2. Create `Student` (inherits `User`).
3. Flush session to persist base and subclass tables.
4. Create `HelpDeskAssistant` tied to existing student.
5. Add course capabilities.
6. Mark registration approved & add notification.
7. Commit transaction.
8. Query staged `RegistrationAvailability` rows and create real `Availability` rows (each committed via helper or could be batched—currently acceptable volume).

---
## Why Each Issue Happened
| Issue | Underlying Concept | Explanation |
|-------|--------------------|-------------|
| FK failure (registration) | Referential integrity | Child (`availability`) required parent (`student`) that didn't yet exist. |
| FK failure (approval) | Transaction ordering | Parent not yet flushed/committed when child rows inserted. |
| Duplicate key on `users` | ORM inheritance | Creating both base (`User`) and subclass (`Student`) duplicates same PK insert. |

---
## Testing Performed
1. Register new assistant with availability + courses.
2. Confirm only `registration_request`, `registration_availability`, and related staging rows exist pre-approval.
3. Approve as admin: no FK or unique violations.
4. Post-approval verification: rows in `users`, `student`, `help_desk_assistant`, `course_capability`, `availability`; staged availability untouched (or optionally prunable later).
5. Login succeeds for approved assistant.

---
## Potential Enhancements (Optional)
- Automatically delete `RegistrationAvailability` rows after migration to keep staging clean.
- Batch insert availability in one session commit for minor performance gain.
- Add uniqueness constraint `(registration_id, day_of_week, start_time, end_time)` to prevent duplicate staged slots.
- Add unit tests simulating full registration + approval lifecycle.
- Consider wrapping availability migration in same transaction by flushing assistant first and deferring helper function commits (requires adjusting `create_availability`).

---
## Maintenance Notes
- Avoid calling `User(...)` directly when creating a student; always instantiate `Student` to preserve polymorphic integrity.
- Any future assistant-related pre-approval data should use a parallel staging table (mirroring `RegistrationAvailability`).
- Keep controller functions free of implicit commits inside loops to maintain transactional clarity.

---
## Summary
The root causes were premature creation of FK-dependent rows and duplicate persistence of a polymorphic base record. Introducing a staging table, enforcing correct commit ordering, and removing redundant user creation resolved all integrity errors. The registration-to-approval pipeline is now consistent, transactional, and extensible.

---
