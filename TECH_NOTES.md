# Technical Notes

## Scope and source of truth

[`./docs/problem-statement.md`](./docs/problem-statement.md) is the binding
source for product behavior. [`./docs/solution-blueprint.md`](./docs/solution-blueprint.md)
records the design approach; the implementation plan is supporting context.

This is a deliberately small, single-workspace MVP: no login, tenancy,
background scheduler, offer-redemption engine, coupon code, OTP, or independent
link expiry. Campaign status—not the campaign window—is authoritative for public
visibility and enrollment.

## Runtime and local environment

Docker Compose is the recommended and self-contained runtime. The `web` image
uses Python 3.13, installs the locked Python dependencies with `uv`, builds the
locked frontend dependencies with Node, then starts Django after PostgreSQL and
Redis report healthy. Compose injects `db` and `redis` service addresses, so no
host Python, Node, PostgreSQL, or Redis installation is needed. The exact
command is `docker compose up --build`; `README.md` contains the operational
commands and container-based verification steps.

## What is implemented

- Internal campaign list, draft builder, typed repeatable offers, lifecycle
  controls, live-link distribution, and aggregate enrollment counts.
- Public mobile-first campaign page with invalid-link and all non-live states.
- Three parameterized offer types: product percent discount, cart fixed
  discount, and sticker earn. Multiple offers of the same type are supported.
- Local SVG QR generation, opaque public UUID links, and idempotent shopper
  enrollment by email or phone.

## Design decisions requested by the exercise

### 1. Validation

The server is authoritative. Django forms provide field feedback; domain
services validate typed offer parameters, lifecycle readiness, and identity
normalization; database constraints protect persisted invariants. JavaScript is
only progressive enhancement: it shows the selected offer type’s fields and
adds/removes offer rows, but direct POST requests receive the same server-side
rules. This avoids client/server rule drift.

A draft may be incomplete. Schedule and launch re-check persisted offers and a
complete UTC window (`end > start` and not already ended). Offer parameters are
validated against the fixed catalog before a draft write succeeds.

### 2. Lifecycle and legal actions

`Campaign.status` is a forward-only state machine with explicit commands:

```text
draft ──schedule──> scheduled ──launch──> live ──end──> ended
  └────────────────launch───────────────────┘
```

There is no generic status-update endpoint. The transition service locks the
campaign row, checks the action against one allowed-transition map, revalidates
readiness for schedule/launch, and writes the next status. The UI derives which
buttons to show from the same policy, while the server remains the final
authority.

`end` is implemented as `live -> ended`. This is the narrow interpretation of
the exercise wording: it closes open enrollment, and the exercise does not
define cancelling a draft or scheduled campaign. A live campaign stays live
after its `ends_at` timestamp until explicitly ended.

### 3. Stale state and concurrent writes

Campaigns carry an integer `version`. Draft saves and lifecycle actions submit
that version, then compare it with the locked current row inside a transaction.
A mismatch—or a draft that became non-editable—returns a conflict without
overwriting current state. This protects the case where one operator launches a
campaign while another still has its draft form open.

### 4. Distribution link and QR code

Every campaign has a stable, opaque UUID (`public_id`) separate from its
internal database ID. The shared link is `/campaigns/c/<public_id>/`; it exposes
no campaign name, offer value, identity, internal key, or independent expiry.
The QR code is generated locally as inline SVG via `qrcode`, so the demo does
not call or leak URLs to a third-party QR service.

Links remain resolvable after state changes. The public route returns a
status-specific draft, scheduled, or ended page without offers; malformed and
unknown IDs return a deliberate invalid-link response.

### 5. Identity without authentication

The shopper submits one unverified email address or phone number, as required.
Emails are trimmed and lowercased. Phone numbers have spaces and punctuation
removed, then require 7–15 digits; this is pragmatic normalization, not full
E.164 validation.

`Enrollment` stores both the submitted and normalized values. A database unique
constraint on `(campaign, normalized_identity)` is the final duplicate guard.
If an insert races or repeats, the existing enrollment is returned as
“recognized,” not an error or second membership. Enrollment also re-checks that
the campaign is still live inside its transaction.

### 6. One model, two audiences

Internal and public representations are separated through distinct presenters,
views, and templates. Internal pages include operational state, lifecycle
controls, share tools, and aggregate enrollment count. Public pages contain only
the campaign identity and formatted offers, and only for a live campaign after
successful/recognized enrollment. Non-live public states intentionally disclose
no offers or internal operational fields.

## Interface and accessibility choices

The internal surface uses centralized `--ll-*` tokens: deep ink navigation,
indigo primary action, teal launch action, neutral surfaces, semantic status
color, compact grids, and responsive cards. These are a documented modern
fallback, not claimed official LoopLink brand colors; replacing tokens is
centralized if verified assets become available.

The builder reveals only the selected offer type’s two parameters. The terminal
end action uses a native confirmation dialog. Forms prevent repeat submission,
validation responses focus the first invalid field, and the distribution URL is
always visible in addition to copy-link support. Public pages are designed for a
narrow mobile viewport.

## How to exercise the key flows

Use the exact setup commands in `README.md`, then open `/campaigns/`.

1. Create a draft with a name but no offer/window and choose **Launch** to see
   server-rendered readiness feedback.
2. Add a valid UTC window and one or more offers; schedule it, open it, and use
   **Launch campaign**. Launching directly from draft is also supported.
3. From the live view, open/copy the UUID link or scan its local QR code.
4. Enroll using `person@example.com`, then repeat with
   ` PERSON@EXAMPLE.COM `; the second visit is recognized and the internal
   aggregate remains one.
5. End the campaign and reload the same link: it shows ended with no offers.
6. Open `/campaigns/c/not-a-public-id/` for the invalid-link state. Open a
   known draft or scheduled UUID link for the non-live scan state.

## Verification

The test suite covers model constraints, offer validation, legal/illegal
lifecycle changes, stale writes, identity normalization, duplicate enrollment,
public visibility, invalid links, QR distribution, and enrollment counts.
Run:

```sh
docker compose exec web pytest
docker compose exec web ruff check looplink
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
```

## Timebox cuts and limitations

- No authentication, team/workspace isolation, audit trail, pagination,
  filtering, analytics, or activity feed.
- No automatic scheduling/ending; dates are validated metadata by specification.
- Monetary parameters are plain numbers in one implied currency; no FX or
  minor-unit handling.
- No offer redemption, coupon generation, SKU lookup, or identity ownership
  verification.
- Clipboard copying depends on the browser API, with a read-only URL fallback.

## AI use

AI assistance was used for planning, code drafting, test creation, UI review,
and iterative debugging. The resulting implementation, trade-offs, and tests
were inspected and can be explained or changed directly.

## What I would do next

Before expanding internal controls, add authentication and workspace ownership.
For production readiness, add audit events, scheduling infrastructure,
observability, security headers/CSP, browser-level accessibility regression
tests, and stronger identity verification only if the product requires it.
