"""Provider-neutral, bounded selection policy for one Owner instruction.

This module never runs models. A cloud coordinator may supply scoped work items
from repository inspection, but a deterministic CLI must not invent filenames.
All capability/cost ratings are operator-supplied estimates, not provider facts.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from codex import dual

PROVIDERS_FILE = Path(__file__).with_name("providers.json")
MAX_PROMPT = 4000
MAX_ITEMS = 8
BLOCKED_SECRETS = re.compile(
    r"(?i)(?:-----BEGIN [A-Z ]*PRIVATE KEY|gh[pousr]_[a-z0-9]{12,}|"
    r"(?:api[_-]?key|password|senha|secret|access[_-]?token)\s*[:=]\s*\S+)"
)
HIGH_SIGNALS = ("deadlock", "race condition", "regressao complexa", "regressão complexa",
                "root cause", "segurança crítica", "segurança", "seguranca", "concorrência",
                "concorrencia", "critical security", "migração irreversível", "irreversible")
LOW_SIGNALS = ("corrige um typo", "typo", "ortografia", "formatar", "ajusta o readme", "fix spelling")
MULTISTEP_SIGNALS = ("implementar", "implement", "integrar", "integration", "testar", "test",
                     "desenvolver", "develop", "criar", "build", "refactor", "refator")
ITEM_ID = re.compile(r"[a-z][a-z0-9-]{0,39}\Z")


class RoutingError(ValueError):
    pass


def _text(value: Any, minimum: int = 12, maximum: int = MAX_PROMPT) -> str:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise RoutingError("A valid bounded instruction is required")
    if any(ord(c) < 32 and c not in "\n\t" for c in value) or BLOCKED_SECRETS.search(value):
        raise RoutingError("Control characters or possible credentials in the instruction")
    return value.strip()


def _validate_item(raw: Any) -> dict:
    if not isinstance(raw, dict) or not {"id", "task", "paths"} <= raw.keys():
        raise RoutingError("Each work item must include id, task and owned paths")
    if set(raw) - {"id", "task", "paths", "depends_on", "reasoning_effort"}:
        raise RoutingError("Unexpected work-item field")
    identifier = raw["id"]
    if type(identifier) is not str or not ITEM_ID.fullmatch(identifier):
        raise RoutingError("Invalid work-item identity")
    task = _text(raw["task"], 12, 3000)
    paths = raw["paths"]
    if not isinstance(paths, list) or not 1 <= len(paths) <= 20 or len(paths) != len(set(map(str, paths))):
        raise RoutingError("Each work item requires bounded unique owned paths")
    if not all(dual._is_safe_path(p) for p in paths):
        raise RoutingError("Unsafe work-item path; inspect repository scope")
    deps = raw.get("depends_on", [])
    if (not isinstance(deps, list) or len(deps) > MAX_ITEMS
            or not all(type(d) is str and ITEM_ID.fullmatch(d) for d in deps)
            or len(set(deps)) != len(deps)):
        raise RoutingError("Invalid work-item dependencies")
    effort = raw.get("reasoning_effort", "auto")
    if type(effort) is not str or effort not in dual.LEVELS:
        raise RoutingError("Invalid requested reasoning effort")
    return {"id": identifier, "task": task, "paths": paths,
            "depends_on": deps, "reasoning_effort": effort}


def _has_overlap(left: dict, right: dict) -> bool:
    return any(a == b or a.startswith(b + "/") or b.startswith(a + "/")
               for a in left["paths"] for b in right["paths"])


def _classify_effort(task: dict) -> str:
    if task["reasoning_effort"] != "auto":
        return task["reasoning_effort"]
    prompt = task["task"].casefold()
    if any(signal in prompt for signal in HIGH_SIGNALS):
        return "high"
    # Low is appropriate only for very narrow edits with no substantive risk.
    if len(prompt) <= 160 and any(signal in prompt for signal in LOW_SIGNALS) and not any(
        signal in prompt for signal in ("security", "segurança", "production", "produção", "migration", "migração")
    ):
        return "low"
    return "medium"


def _load_profiles(registry: Any) -> list[dict]:
    if not isinstance(registry, dict) or registry.get("version") != 1 or not isinstance(registry.get("providers"), list):
        raise RoutingError("Unsupported capability registry")
    profiles = []
    for provider in registry["providers"]:
        if not isinstance(provider, dict) or set(provider) != {"id", "adapter", "enabled", "models"}:
            raise RoutingError("Invalid provider declaration")
        if not isinstance(provider["id"], str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,32}", provider["id"]):
            raise RoutingError("Invalid provider id")
        if provider["adapter"] not in ("codex-cli", "host-unconfigured") or type(provider["enabled"]) is not bool:
            raise RoutingError("Unsupported provider adapter")
        if not isinstance(provider["models"], list) or len(provider["models"]) > 12:
            raise RoutingError("Invalid model registry")
        for model in provider["models"]:
            if not isinstance(model, dict) or set(model) != {"id", "quality_tier", "relative_cost", "capabilities", "efforts", "attested"}:
                raise RoutingError("Invalid model capability profile")
            if not isinstance(model["id"], str) or not re.fullmatch(r"[a-zA-Z0-9._-]{1,64}", model["id"]):
                raise RoutingError("Invalid model id")
            if type(model["quality_tier"]) is not int or not 1 <= model["quality_tier"] <= 5:
                raise RoutingError("Invalid operator-declared capability tier")
            cost = model["relative_cost"]
            if cost is not None and (type(cost) is not int or not 1 <= cost <= 100):
                raise RoutingError("Invalid relative cost (unknown must be null)")
            if not isinstance(model["capabilities"], list) or not all(x in {"code_edit", "code_review", "research", "planning"} for x in model["capabilities"]):
                raise RoutingError("Invalid model capabilities")
            if (not isinstance(model["efforts"], list) or not model["efforts"]
                    or not all(type(e) is str for e in model["efforts"])
                    or not set(model["efforts"]) <= dual.LEVELS):
                raise RoutingError("Invalid supported effort choices")
            if type(model["attested"]) is not bool:
                raise RoutingError("attested must be boolean")
            if provider["enabled"] and model["attested"]:
                profiles.append({"provider": provider["id"], "adapter": provider["adapter"], **model})
    return profiles


def load_registry(path: Path = PROVIDERS_FILE) -> dict:
    if not path.is_file() or path.stat().st_size > 32_000:
        raise RoutingError("Capability registry missing or unbounded")
    data = json.loads(path.read_text(encoding="utf-8"))
    _load_profiles(data)
    return data


def _select_model(profiles: list[dict], capability: str, reasoning: str, allowed: set[str] | None = None) -> dict:
    candidates = [p for p in profiles if capability in p["capabilities"] and reasoning in p["efforts"]
                  and (allowed is None or p["provider"] in allowed)]
    if not candidates:
        return {"status": "no_attested_provider", "reason": "No enabled, attested model for this capability and effort"}
    floor = {"low": 2, "medium": 3, "high": 4}[reasoning]
    adequate = [p for p in candidates if p["quality_tier"] >= floor]
    if not adequate:
        return {"status": "no_adequate_provider",
                "reason": "No attested model meets the configured capability floor; never silently downgrade"}
    pool = adequate
    # Do not silently substitute an unmeasured cheap model for a capable one.
    # Without declared cost, prefer the best attested capacity, not a guessed discount.
    chosen = min(pool, key=lambda p: (p["relative_cost"] is None,
                                      p["relative_cost"] if p["relative_cost"] is not None else 0,
                                      p["quality_tier"] if p["relative_cost"] is not None else -p["quality_tier"],
                                      p["provider"], p["id"]))
    return {"status": "selected", "provider": chosen["provider"], "adapter": chosen["adapter"],
            "model": chosen["id"], "reasoning_effort": reasoning,
            "capacity_assessment": "adequate_by_operator_profile" if adequate else "below_declared_floor",
            "relative_cost": chosen["relative_cost"],
            "cost_source": "operator_profile_not_live_billing"}


def _safety(request: str) -> list[str]:
    text = request.casefold()
    flags = []
    if any(t in text for t in ("produção", "production", "deploy", "release", "credencial", "credential",
                               "apagar base de dados", "delete database", "delete users", "permissões", "permissions")):
        flags.append("material_boundary_requires_project_leader_controls")
    return flags


def _task_expensive(item: dict) -> bool:
    lower = item["task"].casefold()
    return _classify_effort(item) == "high" or len(lower) >= 130 or sum(s in lower for s in MULTISTEP_SIGNALS) >= 2


def plan(order: dict, registry: dict | None = None) -> dict:
    """Choose model, reasoning and one/two workers; no models are started."""
    if not isinstance(order, dict) or set(order) - {"request", "target_repository", "work_items",
                                                       "preference", "capability", "providers"}:
        raise RoutingError("Unexpected order fields")
    request = _text(order.get("request"))
    repo = order.get("target_repository")
    if type(repo) is not str or not dual.REPO_NAME.fullmatch(repo) or repo.casefold() == "martaxi-boss/project-leader":
        raise RoutingError("Invalid target or protected universal Project Leader repository")
    preference = order.get("preference", "auto")
    if preference not in {"auto", "single", "parallel", "serial"}:
        raise RoutingError("Invalid execution preference")
    capability = order.get("capability", "code_edit")
    if capability not in {"code_edit", "code_review", "research", "planning"}:
        raise RoutingError("Unsupported requested capability")
    allowed_raw = order.get("providers")
    if allowed_raw is not None and (not isinstance(allowed_raw, list) or not allowed_raw or
                                    not all(type(v) is str and re.fullmatch(r"[a-z][a-z0-9-]{0,32}", v) for v in allowed_raw)):
        raise RoutingError("Invalid provider allowlist")
    allowed = set(allowed_raw) if allowed_raw else None
    if not isinstance(order.get("work_items"), list) or not 1 <= len(order["work_items"]) <= MAX_ITEMS:
        # A natural-language coordinator should inspect the workspace and submit bounded items.
        return {"version": 1, "status": "needs_scoping", "request": request,
                "target_repository": repo, "reason": "Safe path ownership cannot be inferred from unscoped natural language. The host coordinator must inspect the target and scope work internally; do not ask Owner to split tasks.",
                "agent_count": 0, "mode": "not_started", "warnings": _safety(request)}
    items = [_validate_item(x) for x in order["work_items"]]
    if len({x["id"] for x in items}) != len(items):
        raise RoutingError("Duplicate agent ids")
    ids = {x["id"] for x in items}
    for x in items:
        if any(d not in ids or d == x["id"] for d in x["depends_on"]):
            raise RoutingError("Unknown or self-referencing dependency")
    # Stable topological sort: dependent work cannot launch before prerequisites.
    ordered = []
    pending = list(items)
    while pending:
        ready = [i for i in pending if set(i["depends_on"]) <= {x["id"] for x in ordered}]
        if not ready:
            raise RoutingError("Cyclic dependencies")
        for x in ready:
            ordered.append(x)
            pending.remove(x)
    items = ordered
    has_deps = any(x["depends_on"] for x in items)
    overlap = any(_has_overlap(a, b) for i, a in enumerate(items) for b in items[i+1:])
    if preference == "parallel" and (len(items) < 2 or has_deps or overlap):
        raise RoutingError("Parallel requested but tasks are dependent, overlapping or incomplete")
    if len(items) == 1 or preference == "single":
        mode = "single"
    elif preference == "serial":
        mode = "serial"
    elif preference == "parallel":
        mode = "parallel"
    elif has_deps:
        mode = "serial" if len(items) >= 3 or all(_task_expensive(x) for x in items) else "single"
    elif overlap:
        mode = "single"
    elif sum(_task_expensive(x) for x in items) >= 2:
        mode = "parallel"
    else:
        mode = "single"

    def group(identifier: str, group_items: list[dict]) -> dict:
        instruction = "Complete the following bounded tasks in sequence. Do not exceed assigned paths:\n" +                       "\n".join(f"{i+1}. {x['task']}" for i, x in enumerate(group_items))
        if len(instruction) > 3000:
            raise RoutingError("Aggregated instruction is too large; narrow internal work batches")
        levels = [_classify_effort(x) for x in group_items]
        effort_choice = "high" if "high" in levels else "medium" if "medium" in levels or len(group_items) > 1 else "low"
        return {"id": identifier, "task": instruction,
                "paths": list(dict.fromkeys(p for x in group_items for p in x["paths"])),
                "depends_on": [], "reasoning_effort": effort_choice}

    if mode == "single":
        tasks = items if len(items) == 1 else [group("combined", items)]
    elif len(items) == 2:
        tasks = items
    elif mode == "serial":
        mid = max(1, len(items) // 2)
        tasks = [group("phase-one", items[:mid]), group("phase-two", items[mid:])]
        tasks[1]["depends_on"] = ["phase-one"]
    else:
        # Greedy work balancing, only after proving pairwise disjoint scopes.
        groups = [[], []]
        workloads = [0, 0]
        for x in sorted(items, key=lambda item: -len(item["task"])):
            index = 0 if workloads[0] <= workloads[1] else 1
            groups[index].append(x)
            workloads[index] += len(x["task"])
        tasks = [group("parallel-one", groups[0]), group("parallel-two", groups[1])]
    registry = registry if registry is not None else load_registry()
    profiles = _load_profiles(registry)
    assigned = []
    for t in tasks:
        effort = _classify_effort(t)
        selected = _select_model(profiles, capability, effort, allowed)
        assigned.append({"id": t["id"], "task": t["task"], "paths": t["paths"],
                         "depends_on": t["depends_on"], "selection": selected})
    ready = all(x["selection"]["status"] == "selected" for x in assigned)
    # A second agent is never justified merely because a task has many sequential phases.
    return {"version": 1, "status": "planned" if ready else "blocked_no_provider", "request": request,
            "target_repository": repo, "capability": capability,
            "mode": mode, "agent_count": len(assigned), "tasks": assigned,
            "warnings": _safety(request + "\n" + "\n".join(t["task"] for t in tasks)),
            "rationale": "parallel only for separate costly scopes" if mode == "parallel" else
                         "sequential dependency" if mode == "serial" else "one capable agent avoids coordination overhead",
            "integration": "manual validated PR; never merge/deploy automatically",
            "execution": "local CLI requires --execute and verified adapter; cloud delegation needs live host integration"}
