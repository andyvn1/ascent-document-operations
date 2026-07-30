# ADR-0002: Local AI as a Private Inference Worker

## Decision

When a local AI provider is eventually added, it will operate strictly as
a private inference worker behind the `AIProvider` protocol. It will never
host the public application, authentication, the database, or any
customer-facing endpoint, and the cloud application will always be able to
fall back to a cloud AI provider if the local worker is unavailable.

## Context

The long-term goal (master plan §4) is to move suitable AI inference
workloads to a local AI server for cost and control reasons. Without a
clear boundary, "local AI" could creep into becoming a dependency for
things it should never touch — the public app, auth, or the database —
which would introduce availability and security risk tied to
infrastructure outside the cloud's operational guarantees.

## Options Considered

1. **Local AI as an isolated inference worker only, reached by the cloud
   over a secure tunnel, with mandatory cloud fallback.** (Chosen.)
2. **Local AI as a general-purpose secondary application server** — host
   some business logic or endpoints locally to reduce cloud cost further.
3. **No local AI at all** — stay cloud-only indefinitely.

## Decision Rationale

- Constraining local AI to inference-only keeps a single, well-understood
  failure mode: if it's unreachable, inference falls back to the cloud
  provider, and nothing customer-facing is affected.
- The `AIProvider` protocol (`generate_structured_output`, `generate_text`,
  `create_embeddings`) already defines the entire surface area a provider
  needs to implement — there is no reason for a provider implementation to
  also serve HTTP traffic to end users.
- Option 3 (no local AI) is rejected because it's an explicit goal (master
  plan goal 7) and cloud AI API costs at scale are a real reason to keep
  the option open — but "later" is fine; nothing about the MVP requires it
  now.

## Tradeoffs

- Requires building and maintaining a secure tunnel/VPN and
  service-to-service authentication between cloud and the local worker
  (deferred to TASK-013, not designed here).
- Local AI's cost/control benefits are not realized until that migration
  actually happens — this ADR only guarantees the migration won't require
  re-architecting the provider layer when it does.

## Migration Impact

Enforces that all current and future AI-calling code goes through the
`AIProvider` protocol (see [ADR-0001](0001-cloud-first-architecture.md) and
`docs/architecture/local-ai-migration-plan.md`) rather than calling a
vendor SDK directly. This is what makes adding a local provider later a
new implementation of an existing interface, not a rewrite of calling code.