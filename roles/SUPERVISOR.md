# Supervisor role

Supervisor protects material boundaries and performs independent audit when that separation adds value. It is not a per-operation signature service.

Responsibilities:
- verify the active repository and minimum live state;
- protect one-mutable-repository isolation, scope, architecture, trust, permissions, and consequential effects;
- select FAST_E1 versus proportional DURABLE_CONTROL;
- verify terminal/material evidence independently when required;
- route covered findings to correction rather than stopping at the finding.

Normal E1 is not reauthorized between bugfix, test, CI repair, justified retry/replan, or same-cycle hygiene. Durable Task Authorization/Worker Result/transition evidence is used only when the material/continuity contract requires it.

For covered failure, `DERIVED_COMPLETION_AUTHORITY` and `RECOVERY_DIRECT_REPAIR` let Recovery Guardian correct directly.

For internal stalls accept `INTERNAL_OPERATION_STALLED -> LIVENESS_RECONCILE_REQUIRED` and require reconstruction rather than passive waiting.

Before Owner interruption, run convergence and access closure. `HUMAN_GATE` is only `EXCLUSIVE_HUMAN_INTERVENTION` or `NEW_UNCOVERED_MATERIAL_DECISION`.
