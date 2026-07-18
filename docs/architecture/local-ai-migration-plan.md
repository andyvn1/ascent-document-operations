# Local AI Migration Plan — High-Level Role

> Draft v0.1. This is the high-level "what role does local AI play"
> document required by TASK-004. Detailed networking, authentication,
> deployment, and benchmarking steps belong to TASK-013 (Project 13: Local
> AI Migration) and must not be built before the cloud MVP works.

## Why this exists before any local AI code is written

The provider abstraction (`AIProvider` protocol — see
[ADR-0002](decisions/0002-local-ai-private-inference-worker.md)) only pays
off if the architecture is shaped for a second provider from day one, even
though the MVP ships with a single cloud provider. This document defines
that shape so later work (TASK-016–017 provider system, TASK-013 local
migration) has a target to build toward instead of retrofitting one.

## Role of the local AI worker

- Operates as a **private inference worker**, not a customer-facing
  service. It never hosts the public app, auth, database, or any
  customer-visible endpoint.
- Connects to the cloud application over a secure tunnel/VPN — the cloud
  reaches in to submit inference work, not the other way around.
- Implements the exact same `AIProvider` protocol
  (`generate_structured_output`, `generate_text`, `create_embeddings`) as
  the cloud provider, so business logic in `apps/worker` is unaware of
  which provider is actually serving a given request.
- Candidate workloads (per master plan §4): document classification,
  structured extraction, embedding creation, summarization, background
  processing, document search, batch evaluation.

## What must exist before migration is attempted

1. A working cloud-provider implementation of `AIProvider` in production
   use (TASK-016–017).
2. Provider routing/selection driven by configuration, not code changes.
3. Health checks, timeouts, and retries already proven against the cloud
   provider, so the same reliability contract can be asked of a local
   provider.
4. Cloud fallback: if the local worker is unreachable or unhealthy, the
   system falls back to the cloud provider automatically rather than
   failing the request.

## Explicitly deferred to TASK-013

- Secure tunnel/VPN design and setup.
- Local worker deployment and container configuration.
- Service-to-service authentication between cloud and the local worker.
- Worker heartbeat / health reporting.
- Job-routing rules (which workloads go local vs. cloud, and why).
- Model benchmarking and cost comparison.
- Customer usage quotas tied to provider choice.
- Outage procedure if the local worker goes down.

## Non-negotiable constraint

Regardless of how this evolves, the local AI worker must never become a
path to bypass the human-approval gate, tenant isolation, or the
audit-log requirements defined in AI.md and
`docs/product/requirements.md`. It is an inference backend, not a
decision-maker.