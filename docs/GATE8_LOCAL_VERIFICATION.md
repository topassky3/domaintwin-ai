# Gate 8 local verification checkpoints

This companion file is intentionally short. Use `docs/GATE8_EMERGENCY_DOMAIN.md` for the full protocol.

The local operator should stop at each checkpoint and preserve console/UI evidence:

- Checkpoint A: branch + migrations + tests + contracts + build.
- Checkpoint B: safe runtime (`sandbox`, DNS mutations off, registration off).
- Checkpoint C: read-only Search / Check / Preview in `/app/emergency`.
- Checkpoint D: controlled sandbox registration runtime armed only after C passes.
- Checkpoint E: approved `Register + clone + verify` reaches `READY` and `MATCH YES`.
- Checkpoint F: runtime reset to all mutation/registration flags off.
- Checkpoint G: final regression and clean working tree.

Do not merge the Gate 8 PR until all seven checkpoints have evidence.
