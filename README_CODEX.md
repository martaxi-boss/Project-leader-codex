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
in a trusted Codex project where multi-agent is supported. The automatic policy
selects one or two workers; the two-thread setting is a ceiling, not a requirement
to launch two. Verify the actual selected worker count and the resulting worker
run IDs/evidence. Two Codex Cloud environments cannot be selected at the same
time merely by choosing this repository.

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
It creates **independent Git clones** (no shared refs, object store,
alternates or source remote) and private logs, preserves workspaces, and never
pushes, merges or deploys automatically. Detached HEAD and all other Git refs
are audited, including concealed side refs. Inspect `result.json`, review
changes and validate before opening a PR. Serial mode runs two jobs in
sequence against one private clone so the second sees the first's edits.

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

## Planeamento sem escolher manualmente os agentes

Em `codex.smart`, o utilizador pode fornecer uma única ordem com apenas
`request` e `target_repository`. Com `--repo-dir` apontado a uma cópia
Git limpa e autenticada, `codex.scope_discovery` pode identificar
automaticamente áreas existentes do código e gerar as subtarefas.
Se a ordem não permitir identificar áreas seguras, devolve
`needs_scoping` e exige inspeção adicional por um coordenador com
acesso real ao projeto. Não inventa caminhos, contas ou serviços.
A escolha de modelos bloqueia quando nenhum perfil verificado satisfaz
a capacidade mínima declarada. Desdobramentos e consumo são sempre
testados e relatados, não presumidos.

## Do chat ao executor autenticado

Uma ordem ditada ou escrita no ChatGPT pode ser interpretada por um
coordenador que inspecione o repositorio real, delimite `work_items` e
passe o plano ao gestor `codex.smart`. Este ultimo decide
automaticamente entre um trabalhador, dois em serie ou dois em paralelo
quando recebe caminhos e dependencias verificadas.

**Limite operacional:** a rota autenticada Owner GitHub Issue → Coordenador
com IA independente → `agent_switch` → Codex trabalhador com as regras
canónicas do Project Leader → CI e Supervisor foi comprovada em serviço
real na VPS (execuções 38404860793 e 38414318007, PRs #15 e #16).

A continuação das fases 2 a 8, com nova auditoria no commit integrado,
validação das tarefas originais e identificadores exclusivos por fase,
foi implementada na VPS pela PR #183 e passou os testes automáticos.
**Ainda não existe certificação com uma ordem real de várias fases
dependentes.** O Coordenador não carrega a skill Project Leader:
essa skill é obrigatória nos Codex trabalhadores.

## Entradas universais e estado de certificação — 2026-10-14

A infraestrutura central da VPS foi ampliada sem alterar a Skill Project
Leader original nem a separação das responsabilidades:

- **VPS PR #211**, integrada em `d9fdf130d8644294996e6099607eca45702c1cb8`:
  o Coordenador, o encaminhador e os trabalhadores aceitam repositórios públicos
  existentes e futuros de `martaxi-boss`, desde que a identidade Owner, a
  permissão GitHub de escrita, o `main` exato e os limites sejam verificados.
  Não existe autorização implícita para repositórios privados ou outros Owners.
- **VPS PR #212**, integrada em `b0c26de8792bca3d4f714a519ce4083a48451feb`:
  o bot Telegram existente pode interpretar ordens naturais de correção por
  texto ou voz e encaminhá-las ao mesmo Coordenador por pedido HMAC assinado,
  seguido de Issue criada com a identidade GitHub do Owner. O Supervisor
  continua passivo, sem encaminhar ordens.
- **VPS PR #213**, integrada em `1b33caae45d9baf1faa62b1e56f7d940f9a6764f`:
  projetos com CI condicionado por ficheiros, incluindo PINK IPTV, podem receber
  PRs `PR_STAGED` com estado verdadeiro dos checks. Ausência de checks, `skipped`
  ou PR criada **não** são certificação. A integração automática continua
  limitada ao âmbito documental especializado já aprovado. Noutras bases,
  o integrador regista `PHASE_STAGED_AWAITING_TARGET_CERTIFICATION` sem
  fazer merge, deploy ou arrancar fases dependentes.

As três entradas de ordens pretendidas continuam a ter estados distintos:

- **ChatGPT:** a ligação GitHub do Owner está acessível e pode criar a Issue
  autenticada que já ativa o Coordenador. Não existe garantia de despacho
  automático de qualquer mensagem do chat sem invocação efetiva da ferramenta
  e prova do workflow correspondente.
- **Codex direto:** o circuito GitHub Issue → Coordenador → Codex trabalhador
  está comprovado anteriormente, mas a equivalência entre uma mensagem livre
  enviada diretamente na interface Codex e essa entrada autenticada ainda
  **não está certificada**.
- **Telegram:** ponte e testes automatizados de autenticação, segurança,
  texto e transcrição de voz estão implementados, mas ainda falta observar uma
  ordem real atravessar mensagem → workflow assinado → Issue Owner →
  Coordenador → trabalhador. A disponibilidade do token Owner e do poller
  real deve ser comprovada, não presumida.

**A continuação autónoma das fases dependentes em projetos com validação
específica, como Android/VPN no PINK IPTV, ainda precisa de certificação real.**
Nenhuma destas integrações substitui a revisão de segurança, o teste físico
indispensável ou o controlo exato do projeto-alvo. O teste funcional do PINK
IPTV deve usar uma ordem normal, sem ensinar as regras no pedido, e registar
as evidências do caminho executado.
