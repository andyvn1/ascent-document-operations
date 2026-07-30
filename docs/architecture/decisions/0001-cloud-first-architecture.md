# ADR-0001: Cloud-First Architecture

## Decision

Build the public application, authentication, database, object storage,
job queue, and all customer-facing services in the cloud from the start.
Do not build or depend on any local/private infrastructure for the MVP.

## Context

The long-term plan (master plan §4) is to move some AI inference workloads
to a local AI server to reduce cost and gain control over inference. It
would be possible to design around local infrastructure from day one to
"save the migration later." Building a real, sellable product and
onboarding a pilot customer requires a publicly reachable, reliable
application now, which local infrastructure cannot provide without
significant networking, uptime, and security work that has nothing to do
with proving the product's value.

## Options Considered

1. **Cloud-first for everything customer-facing, local AI added later as an
   inference backend.** (Chosen.)
2. **Hybrid from day one** — run some components locally immediately to
   avoid cloud costs.
3. **Fully local** — self-host the entire application, including the
   public-facing parts.

## Decision Rationale

- A pilot customer needs a reliable, always-on, publicly reachable
  application; a home/local network cannot offer that without disproportionate
  effort relative to what it teaches or proves at this stage.
- Cloud-managed PostgreSQL, object storage, and job queues remove
  operational burden that would otherwise compete with time spent building
  the actual product.
- Keeping the AI inference layer behind the `AIProvider` protocol means the
  cloud-first decision does not block the eventual move of inference
  workloads to a local AI server (see
  [ADR-0002](0002-local-ai-private-inference-worker.md)) — the two
  decisions are independent.

## Tradeoffs

- Ongoing cloud infrastructure cost from day one, even before any paying
  customer exists.
- Less hands-on infrastructure experience early on (mitigated: infrastructure
  skills are still exercised through Docker, CI/CD, and cloud deployment
  tasks later in the roadmap — see Project 12).

## Migration Impact

None yet — this is the starting architecture, not a migration. Future ADRs
(local AI worker networking, cloud fallback) build on top of this decision
without reversing it.