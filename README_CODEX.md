# Project Leader + Codex

This specialized repository is independent from
[the universal Project Leader](https://github.com/martaxi-boss/Project-leader).
Its Git history contains an exact 503-file Project Leader snapshot described
in `UPSTREAM_PROJECT_LEADER.json`. The active fork carries three
narrow, documented compatibility adaptations in its policy, CI workflow
and trusted-gate test fixtures, plus `AGENTS.md`, `CODEX_COORDINATION.md`,
`.codex/config.toml` and `codex/` for dual-agent behavior.

**Original Project Leader remains universal, unmodified, and usable by any
compatible agent.** The new repository selects a Codex-specific extension;
it is not a replacement for the universal plugin.

## In Codex Cloud

Select this new GitHub repository as the source of a *new* Codex Cloud
environment (for example, `Project Leader + Codex`). Codex should read the
root `AGENTS.md` and apply `CODEX_COORDINATION.md` together with the copied
Project Leader Skill. `.codex/config.toml` allows up to two subagent threads
in a trusted Codex project where multi-agent is supported. Test that the two
workers actually ran. Two Codex Cloud environments cannot be selected at the
same time merely by choosing this repository.

## In a signed-in local or VPS Codex CLI

Requires Git, Python >= 3.10, a signed-in `codex` CLI, and a clean clone of
the target project with a verified GitHub `origin` remote. No API keys are
stored here. From the root of this specialized repository:

~~~bash
python -m codex.dual plan --manifest codex/example-order.json
python -m codex.dual run --manifest codex/example-order.json --repo-dir /path/to/target/repo --execute
~~~

The example manifest is **illustrative**; replace ownership paths with real
paths after inspecting the target project. `plan` consumes no Codex tokens.
`run` launches two actual `codex exec` subprocesses (parallel or serial).
It creates isolated Git worktrees and private logs, preserves workspaces,
and never pushes, merges or deploys automatically. Inspect `result.json`,
review changes and validate before opening a PR. Serial mode runs two jobs
in sequence against a shared worktree so the second sees the first's edits.

**Reasoning effort is chosen once per task** (`low`, `medium` or `high`, or
`auto`), not retroactively changed mid-run. This tool does not know the
account's live quota and does not manage the separate VPS soft token ledger.
If authentication, tooling, scopes or concurrency are missing, it fails
rather than fabricating successful execution.

## Update strategy

Treat `UPSTREAM_PROJECT_LEADER.json` as provenance, not a live update feed.
When universal Project Leader changes, compare the canonical pinned source,
update unaffected universal files exactly, preserve the three documented
fork-specific compatibility adaptations, run all tests, and keep the Codex
extension separate. Never edit `martaxi-boss/Project-leader` for Codex requirements.

## Autogestão para agentes na nuvem

O novo gestor em `codex/agent_policy.py` recebe **uma única ordem**. No chat, o
agente coordenador analisa o projeto e constrói internamente as tarefas e os
âmbitos reais; o utilizador não tem de indicar quantos agentes, que modelo ou
que nível de raciocínio usar. A decisão entre um agente, dois em paralelo ou
em série é proporcional à tarefa.

O gestor funciona com um registo extensível de fornecedores, seleção de modelos
por capacidades declaradas e uma ponte para agentes na nuvem com verificação de
resultados. **Apenas o executor local Codex CLI está implementado** neste
momento; Gemini, Claude, Copilot, Antigravity e outros exigem adaptadores e
ligações autenticadas antes de poderem executar tarefas reais.

O consumo dos executores cobertos é contabilizado num registo local privado com
reservas conservadoras quando a telemetria não está disponível. Isto não revela
nem controla as quotas globais da conta. Não há garantia de menor custo para
todas as tarefas.

Consulta [o protocolo completo](codex/SMART_AGENT_ROUTING.md) e o exemplo
[`codex/example-smart-order.json`](codex/example-smart-order.json).
