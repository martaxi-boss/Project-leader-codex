# Project Leader + Codex

> **Estado operativo atual (2026-10-30):** existe um único Coordenador em `codex.smart` e `codex.agent_policy`, pertencente a este repositório. O Codex Cloud executa diretamente quando autenticado; a Skill ChatGPT não inicia um trabalhador sem executor real. A VPS conserva apenas o Supervisor passivo para este projeto e o Telegram é apenas de saída (notificações). As secções datadas sobre o Coordenador da VPS abaixo são histórico, não instruções de ativação.

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

**Writable CLI state in restricted hosts:** the independent codex.smart
and codex.dual CLI runners prefer an explicit --runs-dir when supplied;
otherwise they use a private XDG_STATE_HOME directory, the usual home state
directory, or a configured private XDG_RUNTIME_DIR if home is read-only.
The selected directory must be writable, owned by the current user, and
private (0700), outside the source checkout. Runtime directories may be
ephemeral; keep durable evidence in a persistent authorized location.
A Codex Cloud native worker is a separate authenticated execution path:
if the host prohibits nested codex exec or has read-only Codex credential/
session storage, selecting a writable runs directory alone does **not**
prove that nested CLI can start. Do not copy credentials, weaken sandbox
rules or claim CLI certification from native worker tests.

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

Antes da seleção de agentes, o Coordenador inspeciona o projeto e delimita os
`work_items`, ou o descobridor determinístico `codex.scope_discovery` fá-lo
quando os caminhos são inequívocos. Só depois `codex.agent_policy.plan` recebe
essa ordem delimitada e decide proporcionalmente entre um agente, dois em
paralelo ou em série, incluindo o modelo e o nível de raciocínio. O utilizador
não tem de indicar essas escolhas; ordens sem `work_items` verificáveis
permanecem em `needs_scoping`.

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
coordenador que inspecione o repositório real, delimite `work_items` e
passe o plano ao gestor `codex.smart`. Este último decide
automaticamente entre um trabalhador, dois em serie ou dois em paralelo
quando recebe caminhos e dependencias verificadas.

**Limite operacional:** a rota autenticada Owner GitHub Issue → Coordenador
com IA independente → `agent_switch` → Codex trabalhador com as regras
canónicas do Project Leader → CI e Supervisor foi comprovada em serviço
real na VPS (execuções 38404860793 e 38414318007, PRs #15 e #16).

A continuação ou retoma das fases 2 a 8 verifica externamente o `HEAD` atual e
o resultado certificado da fase concluída, e reutiliza o DAG autorizado da
ordem original, sem criar uma nova ordem nem voltar a invocar o Coordenador IA.
Este mecanismo foi implementado na VPS pela PR #183 e passou os testes
automáticos.
**Certificação real das duas fases documentais — 2026-10-20:** a única ordem
[Owner VPS #288](https://github.com/martaxi-boss/VPS/issues/288) executou
fase 1 (PR #34, quatro checks de CI `success`, merge `dbad4e6`) e arrancou
a fase 2 automaticamente após validação da primeira, sem nova ordem. A fase
2 foi recuperada no mesmo run `39450295755` após correção verificada do
publicador na VPS (PR #289), sem repetir a fase 1: PR #35 com quatro checks
`success` e integração terminal `7f5deef`. Esta evidência **certifica apenas
o circuito real de duas fases documentais e a recuperação específica E1**;
não certifica, por si, operações Android/VPN, execução Codex Cloud com anexos
nem todas as formas de interrupção. O Coordenador não carrega a skill Project
Leader: essa skill é obrigatória nos Codex trabalhadores.

## Fecho canónico: cérebro do Coordenador e poupança de tokens — 2026-10-20

**Decisão expressa do Owner, fechada:** o Coordenador com IA da VPS
**planeia uma vez por ordem original**, após verificar o projeto. O motor de
encaminhamento seleciona o mínimo necessário (um ou, quando justificados,
dois trabalhadores, com raciocínio Low/Medium/High). Cada trabalhador segue
a Skill universal Project Leader e **é responsável por executar, corrigir,
validar e continuar autonomamente no seu âmbito**. A execução das fases
dependentes reutiliza o plano original e verificações externas, **sem
nova análise de IA do Coordenador por fase**. O Supervisor continua
estritamente passivo, com notificações pelo Telegram.

Os rótulos anteriormente sugeridos **"recuperação autónoma geral de falhas"
e "replaneamento contínuo com IA" não constituem funcionalidades
pendentes**: a primeira já está atribuída ao Project Leader no trabalhador,
com falhas externas corrigidas nos respetivos mecanismos; a segunda seria
uma duplicação dispendiosa, por isso **não faz parte da arquitetura**.
Isto não equivale a afirmar que todos os tipos possíveis de avaria já foram
testados. Só uma ordem materialmente nova ou um verdadeiro Human Gate
justificam outro ciclo de autoridade, nunca uma supervisão de IA permanente.

Esta decisão canónica fica documentada aqui e é consistente com o contrato
existente em [CODEX_COORDINATION.md](CODEX_COORDINATION.md), que permanece
inalterado por ser um ficheiro protegido do projeto.
A prova de duas fases e a recuperação específica do publicador estão
documentadas na [Issue VPS #288](https://github.com/martaxi-boss/VPS/issues/288);
o Project Leader universal mantém-se intacto.

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

As entradas atualmente suportadas têm responsabilidades distintas:

- **ChatGPT:** a Skill especializada utiliza o Coordenador deste projeto e ferramentas autenticadas disponíveis. Não existe garantia de despacho real de um trabalhador Codex sem um executor autenticado; não se cria uma Issue na VPS como substituto.
- **Codex direto:** uma tarefa selecionada no Codex Cloud trabalha diretamente no projeto, respeitando o âmbito e os anexos efetivamente disponíveis. A execução autenticada de ponta a ponta com anexos ainda não está certificada. O antigo relay de texto `codex.owner_coordinator_ingress` foi retirado do código ativo; permanece apenas no histórico Git.
- **Telegram:** apenas notificações do Supervisor passivo. A entrada de ordens está desativada por decisão do Owner; as antigas provas de comandos por Telegram são históricas, não uma funcionalidade ativa. O workflow de observação já registou encaminhamento, mas a entrega efetiva no telefone precisa de confirmação.


**A continuação autónoma das fases dependentes em projetos com validação
específica, como Android/VPN no PINK IPTV, ainda precisa de certificação real.**
Nenhuma destas integrações substitui a revisão de segurança, o teste físico
indispensável ou o controlo exato do projeto-alvo. O teste funcional do PINK
IPTV deve usar uma ordem normal, sem ensinar as regras no pedido, e registar
as evidências do caminho executado.

## Ciclo completo das fases — política comum Cloud e VPS

Uma ordem do Owner cobre **todas as fases** autorizadas. O Coordenador analisa
o projeto, determina tarefas e dependências, seleciona trabalho individual,
serial ou até dois Codex independentes em paralelo, e classifica o raciocínio
de **cada fase** como `low`, `medium` ou `high`. O planeador
`codex.agent_policy.plan` conserva todos os itens em `phase_plan`, mesmo
quando agrupa trabalhadores.

O executor `codex.smart.execute_coordinator_phases` aceita as fases
verificadas do Coordenador ou deriva-as de um plano já delimitado, preservando
os níveis de raciocínio. Continua **sem nova ordem** apenas após validação
independente do SHA exato, CI obrigatória e autorização material aplicável.
Uma PR apenas criada (`PR_STAGED`) não é uma integração ou certificação.
Erros recuperáveis exigem correção; não se pede autorização administrativa
para começar a fase seguinte. Não se desativam testes ou proteções de merge.

O **único Supervisor** fica na VPS e acompanha/relata ao Telegram sem aprovar,
despachar, corrigir ou parar fases. Codex Cloud e VPS são duas entradas
independentes para projetos distintos. A integração desta biblioteca não
atualiza automaticamente sessões Cloud antigas nem o workflow que já está
instalado na VPS. Cada host tem de chamar o executor com autenticação e
validador externo reais antes de se declarar continuidade operacional.

## Higiene de contexto e estado comprovado — 15/10/2026

Esta secção **data evidências**; não substitui `AGENTS.md`,
`CODEX_COORDINATION.md`, a Skill canónica, o estado vivo do GitHub nem
autoriza a repetição de uma ordem antiga. As referências operacionais acima,
com data de 14/10/2026, são históricas quando divergem destas verificações.

- **Fonte universal:** `martaxi-boss/Project-leader` `main`
  `b534629851dad20bcf6f9921f3c3a1dbc4ee7248` (Skill 0.7.0).
  Comparação exata das árvores: os 503 ficheiros partilhados com o
  `Project-leader-codex` têm 500 blobs idênticos; só diferem
  `.github/workflows/contract-tests.yml`,
  `projects/policies/project-leader.json` e
  `tests/test_trusted_gate.py` — as três adaptações aprovadas da cópia.
  Nunca propagar regras Codex de volta ao Project Leader universal.
- **Coordenação especializada:** o `main` em
  `0f1aa08ad5b7b5c63323fd20c23243116de49f1c` inclui a
  [PR #32](https://github.com/martaxi-boss/Project-leader-codex/pull/32).
  O motor **único de fases** é `codex.phase_cycle`; o executor local
  `codex.smart.execute_coordinator_phases` e o adaptador de host Cloud
  `codex.cloud_bridge.execute_cloud_coordinator_phases` utilizam esse motor.
  A retomada só pode usar o plano original e um checkpoint
  **independentemente certificado** no SHA atual; não voltar a executar fases
  anteriores por simples perda de contexto.
- **VPS autónoma:** a [PR VPS #234](https://github.com/martaxi-boss/VPS/pull/234)
  foi integrada em `43303b695c68bb79d555a3ea1ec8c0422de7a4e2`.
  O trabalhador VPS já lançado pelo Coordenador existente passa a carregar
  as instruções especializadas **fixadas a um SHA** além da Skill canónica.
  Não foi criado um novo Coordenador, segundo Supervisor ou MCP.
  Testes da PR passaram; não confundir isso com prova de uma nova execução real.
- **Codex Cloud direto:** continua independente da VPS e usa os anexos apenas
  quando estão realmente disponíveis na tarefa privada do Cloud. A interface
  de execução e recuperação tem testes offline; ainda **não há prova de tarefa
  Cloud real com fotografias nem de visibilidade automática desses anexos
  no Supervisor passivo**.
- **PINK #233:** a [PR PINK #69](https://github.com/martaxi-boss/pink-iptv/pull/69)
  teve CI Android terminal `success` sobre o seu HEAD real
  `531044389d43c1541d5b38fbe60f12c9ec8a5a88`
  ([run 38702311695](https://github.com/martaxi-boss/pink-iptv/actions/runs/38702311695))
  e foi integrada como `bd5a5350c2168d1728c812e56b429c5584ca8a39`.
  A fase 2 **não foi executada nem certificada**: a execução inicial
  [VPS #233](https://github.com/martaxi-boss/VPS/issues/233) terminou após
  uma PR preparada e não guardou uma retoma autónoma comprovada do DAG.
  Não repetir a fase 1, recriar a Issue, falsificar checkpoint ou assumir
  aceite o teste físico Android.
- **Branches e evidência:** a [higiene automática 38704064711](https://github.com/martaxi-boss/Project-leader-codex/actions/runs/38704064711)
  terminou com sucesso. Na observação de 15/10 havia 15 branches não-`main`
  ainda divergentes e sem PRs abertas. Preservá-las: não há demonstração de
  que os seus commits únicos tenham sido integrados. Não apagar por idade,
  não reescrever histórico, não remover evidência de auditoria.

Ao iniciar qualquer trabalho futuro, consultar os HEADs, PRs e checks **atuais**.
Um registo `PR_STAGED`, um run de workflow `success` ou a cópia de regras
não certificam automaticamente todas as fases nem o funcionamento num host.
