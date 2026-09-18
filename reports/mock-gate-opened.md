# Mock Kaito gate opened for pipeline testing — SUPERSEDED

> **SUPERSEDED (Phase 12):** Mock references and mock pilot pages must not open production gates.

The earlier intentional mock approval of geometric placeholders and
`KAITO_REFERENCE_APPROVED=true` / `PILOT_APPROVED=true` has been **revoked**.

- Mock pilot pages were moved to `rejected/mock-pilot-pages/`
- Kaito reference slots were demoted to `GENERATED`
- Production gates reset to closed; master design not selected

Regenerate with a REAL backend and select a master design before production.
