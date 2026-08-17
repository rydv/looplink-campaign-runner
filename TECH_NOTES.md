# Tech Notes

## Sources and scope

The binding source for product behavior is
[`docs/problem-statement.md`](../docs/problem-statement.md). When behavior is
unclear, that document takes precedence over implementation convenience. The
secondary design reference is
[`docs/solution-blueprint.md`](../docs/solution-blueprint.md), followed by the
[`docs/multi-stage-implementation-plan.md`](../docs/multi-stage-implementation-plan.md).

This is a single-workspace, single-process MVP. Authentication, multi-tenancy,
automatic scheduling, offer execution, coupon generation, identity verification,
and independent distribution-link expiry are intentionally out of scope.

## Stage 0 decisions

### Validation

The server is authoritative for all domain rules. Browser validation may mirror
simple constraints for immediate feedback, but lifecycle readiness, draft-only
editing, offer parameter validation, identity normalization, and enrollment
uniqueness will be enforced in domain services and the database.

### Lifecycle

Campaign lifecycle changes will use explicit service operations rather than a
general status update. The supported transitions are `draft -> scheduled`,
`draft -> live`, `scheduled -> live`, and `live -> ended`. We interpret `end` as
`live -> ended` because its specified purpose is to close open enrollment; the
exercise does not define draft/scheduled cancellation. Status alone determines
public visibility and enrollment, so dates never transition a campaign.

### Stale writes

Campaigns will carry an integer version. Draft saves and lifecycle actions must
match the persisted version inside a transaction. A version mismatch or a draft
that has become non-draft returns a conflict and never overwrites current state.

### Distribution

Each campaign will have an opaque, stable, unique public identifier. Its QR code
will contain only the absolute public URL. It will not expose an internal primary
key, campaign data, offer values, shopper identity, or an independent expiry.

### Identity and duplicate enrollment

Email is trimmed and lowercased. Phone input has spaces and punctuation removed.
A database unique constraint on campaign plus normalized identity is the final
duplicate guard; a conflicting insert is recovered as a recognized enrollment.

### Two audiences

Internal and shopper pages use separate presenters/templates over the same
domain model. Public presentation is status-gated and never includes offers for
draft, scheduled, or ended campaigns.

### UI direction

No trustworthy color specification is present in the starter. Before the visual
stage, official LoopLink brand assets will be used if a reliable source is
available. Otherwise the product will use a restrained modern commerce-platform
theme: neutral surfaces, strong typographic hierarchy, one primary accent,
semantic status colors, compact responsive grids, and accessible contrast. All
colors will be centralized as design tokens so verified brand values can replace
the fallback without rewriting templates.

The starter's Outfit typeface, Django templates, HTMX actions, Alpine for local
interactions, and Tailwind styling will be retained.

### Provisional UI tokens

The first implementation uses a deep ink navigation surface (`#101323`), an
indigo primary (`#5d4ce6`), a teal operational accent (`#14b8a6`), and neutral
white/slate content surfaces. These are intentionally modern commerce-platform
defaults rather than claimed LoopLink brand values. They live in
`styles/looplink.css` as `--ll-*` tokens, together with shared radii, borders,
and shadows, so an official palette can replace them in one place.

## Environment baseline

- The repository began from commit `062fc69` (`template code`).
- Python 3.13 is the supported project runtime. A host Python 3.14 installation
  is not treated as the project environment.
- PostgreSQL and Redis remain the starter's local Docker-backed services.
- The Stage 0 baseline passes Django system checks, migrations, Ruff, Pytest,
  and the Webpack production build. The starter contained no tests, so a small
  campaign-app registration smoke test was added.
- `npm ci` reports vulnerabilities in the locked starter dependency tree. No
  automatic audit fix was applied because it could introduce unrelated or
  breaking dependency changes; this will be reassessed before submission.

## Stage 2 domain foundation

`Campaign` keeps its internal database identifier separate from an opaque UUID
`public_id`, and includes status, UTC window fields, version, and timestamps.
Drafts may have an incomplete window while they are being built; readiness is
checked only at schedule/launch time. `Offer` is an ordered list—not a map by
type—with JSON parameters validated by the fixed offer catalog. `Enrollment`
stores both original and normalized identity, with a database unique constraint
on `(campaign, normalized_identity)`.

The model layer provides persistence constraints; pure services own offer
parameter validation, lifecycle/readiness rules, identity normalization, and
safe offer formatting. Internal and public presenters are intentionally
separate. The public presenter exposes offers only for `live` campaigns.

## To complete during implementation

- [ ] Example commands and requests for required flows
- [ ] Final list of timebox cuts and known limitations
- [ ] Whether and how AI tools were used
- [ ] What would be implemented next with more time

## Stage 3 internal draft builder

The draft builder is intentionally a server-rendered Django form and inline
formset first, with Alpine only adding repeatable offer rows in the browser.
This keeps direct HTTP submissions, validation errors, and persistence behavior
independent of JavaScript. The write service locks the campaign row, permits
changes only while it is a draft, checks the submitted integer version, and
replaces the ordered offer aggregate atomically. A non-draft edit URL renders a
read-only locked response rather than trusting the client to hide edit controls.

## Stage 4 lifecycle actions

Lifecycle changes go through a separate `transition_campaign` command instead
of the draft write path. It acquires the campaign row lock, verifies the
submitted version and allowed action against current state, re-validates
readiness for schedule/launch, then increments the version with the new status
in the same transaction. The route accepts only POST and the UI only renders
actions returned by the lifecycle policy; those UI controls are guidance, not
the security boundary.

## Stage 5 shopper access and enrollment

Public campaigns are addressed by the opaque UUID alone and are presented by a
separate, deliberately small data shape. Non-live pages disclose neither offers
nor operational details. Enrollment locks and re-checks campaign status at POST
time, then relies on the database uniqueness constraint for cross-request
idempotency. The attempted insert is isolated in a nested transaction so a
duplicate can be recovered as a recognized enrollment without poisoning the
outer transaction.

## Stage 6 distribution

The distribution URL is built from the inbound request and contains only the
campaign's opaque UUID. QR rendering uses the local `qrcode` Python package and
an inline SVG image; it makes no request to a hosted QR service and persists no
derived image. The live-only internal view is the sole place distribution data
is prepared or rendered.
