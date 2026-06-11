# Auth Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Supabase login and password recovery work reliably in the Hostinger frontend.

**Architecture:** Keep Supabase Auth as the single production auth provider. Add a recovery preparation API in `authClient` that validates the `/reset-password` return session before allowing `updateUser({ password })`. Keep local auth as a development fallback, but do not pretend password recovery works without Supabase.

**Tech Stack:** React, Vite, Supabase JS, Node test runner.

---

### Task 1: Recovery Session API

**Files:**
- Modify: `frontend_atual/apps/web/src/lib/authClient.js`
- Test: `frontend_atual/apps/web/src/lib/authClient.test.js`

- [ ] **Step 1: Write failing tests**

Add tests proving that Supabase recovery can exchange a `code` from `/reset-password?code=...`, can accept an already available recovery session, and returns a clear invalid-link error when no session exists.

- [ ] **Step 2: Run tests and verify they fail**

Run: `npm run test --workspace minerva-travel-frontend -- src/lib/authClient.test.js`

- [ ] **Step 3: Implement `preparePasswordRecovery`**

Add `preparePasswordRecovery(currentUrl)` to local, PocketBase, and Supabase clients. Supabase implementation should:
- parse URL errors first;
- exchange `code` with `exchangeCodeForSession` when present;
- otherwise call `getSession`;
- set the local auth model when a session exists;
- return `{ success: false, error }` when there is no valid recovery session.

- [ ] **Step 4: Run tests and verify they pass**

Run: `npm run test --workspace minerva-travel-frontend -- src/lib/authClient.test.js`

### Task 2: Reset Password Page State

**Files:**
- Modify: `frontend_atual/apps/web/src/contexts/AuthContext.jsx`
- Modify: `frontend_atual/apps/web/src/pages/ResetPasswordPage.jsx`
- Test: `frontend_atual/apps/web/tools/hostinger-structure.test.js`

- [ ] **Step 1: Expose recovery preparation through context**

Add `preparePasswordRecovery` to `AuthContext`.

- [ ] **Step 2: Gate the reset form**

Update `/reset-password` to show a loading state while validating the link, show an invalid/expired link state when recovery cannot be prepared, and show the password form only after recovery is valid.

- [ ] **Step 3: Clean the callback URL**

After a successful recovery preparation, replace the browser URL with `/reset-password` so the code/token is not left in the address bar.

### Task 3: Production Build and Deploy

**Files:**
- Update static build in `runtime/hostinger-frontend-static`

- [ ] **Step 1: Verify**

Run:
- `npm run lint --workspace minerva-travel-frontend`
- `npm run test --workspace minerva-travel-frontend -- src/lib/authClient.test.js tools/hostinger-structure.test.js`
- `npm run build --workspace minerva-travel-frontend`

- [ ] **Step 2: Sync Hostinger build**

Run:
- `rsync -a --delete --exclude=.git --exclude=public_html frontend_atual/apps/web/dist/ runtime/hostinger-frontend-static/`
- `rsync -a --delete frontend_atual/apps/web/dist/ runtime/hostinger-frontend-static/public_html/`

- [ ] **Step 3: Commit and push**

Commit `main` and `hostinger-frontend`, then push both branches.
