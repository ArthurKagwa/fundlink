# NGO & Campaign Approval Flow Plan

## Objectives
Define end-to-end process for:
1. NGO application submission, review, approval/rejection
2. Automatic or manual user account provisioning for approved NGOs
3. Campaign creation workflow (draft -> review -> publish)
4. Admin control points & auditability
5. Security, validation, and missing implementation gaps

---
## Current State (From Code Review)
- NGO model has `approved` boolean but no status timestamps or rejection reason.
- Frontend form posts to `/api/ngos/apply/` (custom action) using `NGOApplicationSerializer`.
- NGO auto-approval is NOT performed (good) but no admin endpoint exists to approve.
- User account creation only happens if `password` provided in payload (not currently on HTML form).
- Campaigns have `active` + `published`; viewset filters public list by both + NGO approved.
- No explicit admin endpoints for: NGO approve/reject, campaign publish/unpublish.
- Impact posts have `published` but no admin workflow yet.

---
## Target Lifecycle

### 1. NGO Application
State Machine (proposed):
`draft (optional)` -> `submitted` -> `approved` OR `rejected` -> (optional reapply path)

Minimal extension to existing model:
- Keep `approved` (backwards compat) but add:
  - `status` (choices: submitted, approved, rejected)
  - `approved_at` (DateTime null)
  - `reviewed_by` (FK to `User` staff null)
  - `rejection_reason` (Text null)
  - Migration sets existing approved=True => status=approved.

Submission:
- Endpoint: `POST /api/ngos/apply/`
- Returns: `{id, status: "submitted"}`
- Validation: unique email, unique wallet (case-insensitive), checksum wallet, description length.
- Side effects: optional queued email to staff or Slack webhook.

### 2. NGO Review / Approval
Admin actions (staff only):
- `POST /api/admin/ngos/{id}/approve` -> sets approved=True, status=approved, stamps `approved_at`, associates reviewer, creates user account if missing (with temp password + email invite/reset link).
- `POST /api/admin/ngos/{id}/reject` -> sets status=rejected, stores `rejection_reason` (required), leaves approved=False.
- Optional: `POST /api/admin/ngos/{id}/request_changes` (future) with structured feedback.

Permissions & Security:
- Endpoints protected via staff-only permission & HMAC (if triggered internally by bot/verifier flows, not strictly needed here).

### 3. NGO Authentication
Options:
A. Password set during application (add password + password_confirm fields).
B. Auto-generate password and force reset (send password reset email).
C. Magic-link login (future enhancement).

Baseline Implementation (A):
- Add password fields to form & serializer (write-only).
- Create `User` immediately; restrict token issuance (JWT) until NGO approved.

API Guard:
- Modify login/token issuance view or custom permission to block NGO user whose NGO not approved (return 403 with reason).

### 4. Campaign Workflow
State Machine (proposed):
`draft` -> `submitted_for_review` -> (`published` & `active`) OR `rejected`.

Model Additions:
- Fields to add to `Campaign`:
  - `status` (draft, submitted, approved, rejected)
  - `submitted_at`, `approved_at`, `reviewed_by`, `rejection_reason`
- Retire dual booleans (`active`, `published`) or derive them from `status == approved`.
- Short-term compatibility: keep existing booleans, set them when status changes.

Endpoints:
- NGO creates draft: `POST /api/campaigns/` (status defaults to draft)
- NGO submits for review: `POST /api/campaigns/{id}/submit` (only owner, status draft -> submitted)
- Admin approves: `POST /api/admin/campaigns/{id}/approve` (status submitted -> approved, sets published=True, active=True)
- Admin rejects: `POST /api/admin/campaigns/{id}/reject` with JSON `{reason: "..."}`
- NGO can update while draft or rejected (after changes -> resubmit)

Public Visibility Rule:
- Public list: `status=approved` AND `ngo.status=approved`.

### 5. Impact Posts
Optional moderation (Phase 2):
- Add `status` to `ImpactPost` if needing review; else allow auto-publish for approved NGOs.

### 6. Auditing & Logs
- Add model signals to log transitions to a `ModerationLog` table (generic FK: object id, type, from_status, to_status, reviewer, timestamp, notes).
- Expose admin inline for traceability.

### 7. Email / Notification Hooks (Future)
Events:
- NGO submitted -> staff notification
- NGO approved/rejected -> applicant email
- Campaign submitted -> staff notification
- Campaign approved -> NGO email + triggers bot cache refresh
- Campaign rejected -> NGO email

### 8. Security & Validation Checklist
- Enforce wallet checksum & uniqueness (case-insensitive index suggestion)
- Limit description length (500) & min length (100) server-side
- Rate limit application endpoint (e.g., DRF throttling or IP-based middleware)
- Prevent unapproved NGO from creating/submitting campaigns (permission check in `perform_create` & custom action)
- Ensure only owner NGO manipulates its drafts
- Staff-only endpoints use `IsAdminUser` + potential internal HMAC secret if invoked by background workers

### 9. Missing Pieces (Actionable Gaps)
1. No NGO status field (only `approved` boolean) -> add status workflow fields.
2. No admin approval endpoints for NGOs.
3. No rejection mechanism / reason storage for NGOs or campaigns.
4. No campaign status field; dual booleans cause ambiguity.
5. No serializer for NGO approval / campaign moderation actions.
6. No password capture path in NGO application UX.
7. No permission check to block pre-approval NGO login usage (if undesired).
8. No rate limiting or spam protection on apply endpoint.
9. No auditing / moderation log table.
10. No email notification integration.
11. Wallet checksum currently disabled (web3 commented out); need dependency & migration to normalize existing data.
12. Frontend form JS posts but lacks handling of server validation errors mapping (partial; some logic exists but expects `errors` key not DRF field map directly).
13. No staff UI for listing submitted NGOs/campaigns with filtering by status.
14. Campaign creation currently sets no explicit status sequence; NGOs could potentially toggle `active` via future code changes if not guarded.

### 10. Incremental Implementation Plan
Phase 1 (Core Moderation Backbone):
- Add fields & migrations (NGO: status, approved_at, reviewed_by, rejection_reason; Campaign: status, submitted_at, approved_at, reviewed_by, rejection_reason)
- Backfill existing records
- Add admin actions in Django Admin (approve/reject buttons)
- Implement API endpoints for approve/reject/submit (NGO & Campaign)

Phase 2 (Security & Validation):
- Enable web3 checksum + database normalization
- Add throttling to apply endpoint
- Enforce min/max description lengths server-side
- Add permission class denying campaign creation unless NGO approved

Phase 3 (UX & Notifications):
- Add password fields to application form
- Add email templates & send events
- Improve frontend error display mapping to DRF responses

Phase 4 (Auditing & Logs):
- Create `ModerationLog`
- Signal hooks on status transitions

Phase 5 (Bot Integration Enhancements):
- Endpoint to push cache invalidation when campaign approved
- Bot fetches only approved NGOs & campaigns (already mostly true)

### 11. Data Model Changes (Draft)
```python
class NGO(models.Model):
    # existing fields ...
    status = models.CharField(max_length=20, choices=[('submitted','Submitted'),('approved','Approved'),('rejected','Rejected')], default='submitted')
    approved_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_ngos')
    rejection_reason = models.TextField(blank=True)

class Campaign(models.Model):
    # existing fields ... (consider deprecating active/published)
    status = models.CharField(max_length=20, choices=[('draft','Draft'),('submitted','Submitted'),('approved','Approved'),('rejected','Rejected')], default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='reviewed_campaigns')
    rejection_reason = models.TextField(blank=True)
```
Derived properties:
- `is_live = status == 'approved' and ngo.status == 'approved'`

### 12. Example API Contracts
Approve NGO:
`POST /api/admin/ngos/42/approve/` -> `201 {id:42,status:'approved',approved_at:'...',wallet_address:'...'}`
Reject NGO:
`POST /api/admin/ngos/42/reject/` JSON: `{reason:"Missing legal docs"}` -> `200 {status:'rejected',rejection_reason:'Missing legal docs'}`
Submit Campaign:
`POST /api/campaigns/55/submit/` -> `200 {id:55,status:'submitted'}`
Approve Campaign:
`POST /api/admin/campaigns/55/approve/` -> `201 {id:55,status:'approved',is_live:true}`

### 13. Risks & Mitigations
- Race condition on dual approval changes -> use `select_for_update()` in approve actions.
- Wallet collisions due to lowercase vs checksum -> create UniqueConstraint with `Lower('wallet_address')`.
- Spam applications -> add captcha or minimal hCaptcha if public launch.
- Orphaned campaigns if NGO later rejected -> enforce `ngo.status='approved'` in visibility queries.

### 14. Minimal Next Steps to Start
1. Create migrations adding status/review fields.
2. Add admin inline actions for NGO & Campaign models.
3. Implement API endpoints (custom viewset actions) for approve/reject/submit.
4. Update serializers to surface status + reasons.
5. Adjust public queryset filters to use status fields.

---
## Request for Confirmation
Confirm if you want to proceed with Phase 1 implementation now. Once confirmed, I will:
- Draft migrations
- Patch models, admin, and viewsets
- Add placeholder endpoints

Let me know and I’ll execute Phase 1.
