---
name: build-app
description: Build full-stack applications using the ATLAS framework (5-phase process). Architect, Trace, Link, Assemble, Stress-test. Use when asked to build an app, create a dashboard, make a tool, or develop a full-stack application with database and backend logic. For static websites and landing pages, use build-website instead.
model: opus
context: fork
user-invocable: true
---

# Build App — ATLAS Framework

Build full-stack applications with databases, auth, and backend logic.

## When to Use

- Dashboards and admin panels
- SaaS applications
- Internal tools
- Client portals
- Applications with user accounts and data persistence

**NOT for:** Static websites, landing pages, portfolios → use `build-website` instead.

## The ATLAS Framework

### A — Architect

Define the problem space before writing code.

1. **Problem statement** — What problem does this solve? For whom?
2. **User stories** — 3-5 key user stories (As a [role], I want [action], so that [benefit])
3. **Success metrics** — How do we know it works? (specific, measurable)
4. **Constraints** — Timeline, budget, tech requirements, integrations
5. **Non-goals** — What this app explicitly does NOT do (prevents scope creep)

**Output:** Architecture document with problem, users, stories, metrics, constraints.

### T — Trace

Map the data and integration layer.

1. **Data schema** — Tables, relationships, constraints (draw the ERD mentally)
2. **API design** — Endpoints, methods, request/response shapes
3. **Integrations** — External services, webhooks, OAuth providers
4. **Auth model** — Who can do what? (roles, permissions, row-level security)
5. **Stack proposal** — Framework, database, hosting (justify each choice)

**Recommended stack:**
- **Frontend:** Next.js or React + Tailwind
- **Backend:** Supabase (Postgres + Auth + Realtime + Storage + Edge Functions)
- **Alternative:** SQLite + Express for simple tools

**Output:** Schema diagram, API spec, stack decision with rationale.

### L — Link

Validate connections before building.

1. **Database setup** — Create tables, enable RLS policies, test queries
2. **Auth flow** — Sign up, sign in, role assignment, session handling
3. **API test** — Hit each endpoint, verify response shapes
4. **Integration test** — Connect external services, verify data flow
5. **Environment** — All keys in .env, all configs in args/

**Rule:** Don't write UI until the data layer is validated. Nothing is worse than building a frontend on a broken backend.

### A — Assemble

Build the application, layer by layer.

**Build order:**
1. Database migrations and seed data
2. Backend API / Edge Functions
3. Auth integration
4. Core UI layout (navigation, routing)
5. Feature pages (one at a time, fully functional before moving on)
6. Polish (loading states, error states, empty states)

**Rules:**
- One feature at a time — complete before starting the next
- Every page needs: loading state, error state, empty state, populated state
- API calls should have proper error handling and user feedback
- Never hardcode data — always query the real source

### S — Stress-test

Quality assurance before shipping.

1. **Functional tests** — Every user story works end-to-end
2. **Edge cases** — Empty data, missing fields, expired tokens, concurrent users
3. **Security** — SQL injection, XSS, auth bypass, RLS verification
4. **Performance** — Page load < 2s, API response < 500ms, no N+1 queries
5. **Mobile** — Responsive at all breakpoints
6. **User acceptance** — Does it actually solve the problem from step A?

### Extensions

**+V — Validate (Security Deep Dive)**
- OWASP Top 10 checklist
- Penetration testing for auth flows
- Rate limiting and abuse prevention

**+M — Monitor (Production Readiness)**
- Error tracking (Sentry or equivalent)
- Logging for critical operations
- Uptime monitoring
- Analytics for usage patterns

## Rules

- Always start with Architect — never jump to code
- Database before frontend — validate data layer first
- One feature at a time — resist the urge to parallelize
- Every state matters — loading, error, empty, populated
- Security is not optional — RLS, input validation, auth checks
