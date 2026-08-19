# Gate 8 name.com integration notes

Implementation targets name.com Core API and keeps the first registration flow intentionally narrow:

- registration inventory only;
- non-premium only;
- `.com`, `.net`, `.org` only;
- exact availability re-check before apply;
- persisted idempotency key on Create Domain;
- sandbox-only registration;
- DNS clone followed by provider re-read and exact fingerprint verification.

The narrow scope is deliberate: unsupported acquisition types and premium/TLD-specific cases are rejected rather than approximated.
