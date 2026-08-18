# LoopLink Campaign Builder & Distribution

A Django implementation of the LoopLink engineering exercise: an internal campaign builder and a mobile-first shopper enrollment experience.

The behavioral source of truth is [`../docs/problem-statement.md`](../docs/problem-statement.md). Architecture and staged delivery notes are in [`../docs/solution-blueprint.md`](../docs/solution-blueprint.md) and [`../docs/multi-stage-implementation-plan.md`](../docs/multi-stage-implementation-plan.md).

## Prerequisites

- Docker Desktop with Docker Compose v2

## Setup and run

```sh
docker compose up --build
```

This builds the frontend assets and Python environment inside the application
image, starts PostgreSQL and Redis, applies migrations, and serves Django.
Open [http://127.0.0.1:8000/campaigns/](http://127.0.0.1:8000/campaigns/).

Run in the background with `docker compose up --build -d`; inspect app logs
with `docker compose logs -f web`; stop all services with `docker compose down`.
PostgreSQL and Redis intentionally have no host ports because the app reaches
them through the Compose network as `db` and `redis`.

If a host development server is already using port 8000, stop it before
starting the `web` service, or change the left-hand side of `8000:8000` in
`docker-compose.yml`.

## Use the two surfaces

### Internal builder

1. Create a campaign at `/campaigns/new/` with a name, UTC start/end window, and one or more typed offers.
2. Save drafts freely. Schedule or launch requires a valid, non-ended window and at least one offer.
3. Launch opens enrollment immediately; scheduling first is optional.
4. A live campaign shows a copyable public URL and locally generated QR code.
5. End is explicitly confirmed and permanently closes enrollment.

### Shopper page

Open the live campaign URL or scan its QR code. A shopper enters an email or phone number, then sees the configured offer values. Repeating the same normalized identity is recognized without creating another enrollment.

## Required acceptance walkthrough

1. Try launching a blank draft; observe readiness feedback.
2. Add a valid window and offer, then launch directly.
3. Open the generated public URL and enroll with `person@example.com`.
4. Submit ` PERSON@EXAMPLE.COM ` again; observe the recognized state.
5. End the campaign and reload the same public URL; it renders ended with no offers.
6. Open `/campaigns/c/not-a-public-id/` to verify the intentional invalid-link response.

## Verification

```sh
docker compose exec web pytest
docker compose exec web ruff check looplink
docker compose exec web python manage.py check
docker compose exec web python manage.py makemigrations --check --dry-run
```

## Key implementation choices

- Status is authoritative; dates are metadata and never change status.
- Draft saves and lifecycle actions use row locks plus an integer version.
- Public URLs contain only an opaque UUID; QR generation is local SVG.
- The database unique constraint is the duplicate-enrollment authority.

See [TECH_NOTES.md](TECH_NOTES.md) for trade-offs, limitations, AI use, and the complete decision record.
