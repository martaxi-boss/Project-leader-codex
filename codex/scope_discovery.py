"""Read-only, bounded Git scope discovery for a single natural-language order.

Never fabricates target paths or makes a model/provider call. Ambiguous requests
remain needs_scoping for an authenticated host coordinator to resolve.
"""
from __future__ import annotations

import re
from pathlib import Path
import subprocess
import unicodedata

from codex.agent_policy import RoutingError
from codex import dual

# Portuguese and English project terms. This is a *narrow* low-risk fallback,
# not an LLM task decomposition or an authorization to modify unrelated files.
CONCEPTS = {
    "channels": ("canal", "canais", "channel", "channels"),
    "movies": ("filme", "filmes", "movie", "movies", "film", "films"),
    "series": ("serie", "series", "season", "seasons", "temporada", "temporadas"),
    "players": ("player", "players", "reproducao", "reprodutor", "playback"),
    "menus": ("menu", "menus", "navigation", "navegacao", "navegar"),
    "tests": ("teste", "testes", "test", "tests"),
    "docs": ("documentacao", "documentation", "docs", "readme"),
}
DENY_PARTS = {"node_modules", "vendor", "dist", "build", "target", "__pycache__", "venv", "generated"}
MAX_TRACKED = 6_000


def _norm(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    return "".join(c for c in text if not unicodedata.combining(c))


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", _norm(text)))


def _list_paths(repo_dir: Path, target: str) -> list[str]:
    # Verify the exact target's clean local checkout before consulting its paths.
    dual._preflight(repo_dir, target)
    command = subprocess.run(["git", "-C", str(repo_dir), "ls-files", "-z"],
                             capture_output=True, check=False)
    if command.returncode or len(command.stdout) > 2_000_000:
        raise RoutingError("Unable to enumerate bounded trusted tracked paths")
    raw_paths = command.stdout.decode("utf-8", "strict").split("\x00")
    files = []
    for name in raw_paths:
        if not name:
            continue
        if dual._is_safe_path(name) and not (set(name.lower().split("/")) & DENY_PARTS):
            tracked = repo_dir / name
            if tracked.is_symlink() or tracked.resolve().is_relative_to(repo_dir.resolve()) is False:
                continue  # no symlink escape from the chosen repository
            files.append(name)
            if len(files) > MAX_TRACKED:
                raise RoutingError("Repository is too large for deterministic discovery; use host scoping")
    return files


def discover_work_items(order: dict, repo_dir: Path) -> dict:
    """Supply grounded, nonoverlapping bounded items, or retain needs_scoping.

    This is for recognisable code areas only. It deliberately stops rather
    than guessing a filename in an ambiguous natural-language request.
    """
    if not isinstance(order, dict) or "work_items" in order:
        return order
    request = order.get("request")
    target = order.get("target_repository")
    if not isinstance(request, str) or not isinstance(target, str) or not dual.REPO_NAME.fullmatch(target):
        return order  # canonical planner will explain invalid input
    request_norm = _norm(request)
    # A negated area is never an ownership grant; leave nuanced constraints
    # to the host coordinator instead of accidentally editing excluded files.
    if any(text in request_norm for text in (
        "sem mexer", "sem tocar", "nao mexer", "nao tocar", "nao alter",
        "dont touch", "do not touch", "without changing", "except for", "excluding",
    )):
        return order
    words = _words(request)
    concepts = [name for name, aliases in CONCEPTS.items() if words & set(aliases)]
    primary = [name for name in concepts if name not in {"menus", "tests", "docs"}]
    if primary:
        concepts = primary  # words like 'test' and 'menu' are often work instructions
    if not concepts:
        return order
    tracked = _list_paths(repo_dir, target)
    if not tracked:
        return order
    candidates: dict[str, list[str]] = {}
    for concept in concepts:
        aliases = set(CONCEPTS[concept])
        found = set()
        for file in tracked:
            parts = Path(file).parts
            if len(parts) > 14:
                continue
            for position, segment in enumerate(parts):
                if _words(Path(segment).stem) & aliases:
                    # Prefer a narrow matching code-area directory, or the
                    # exact file when only the filename matches.
                    found.add("/".join(parts[:position+1]))
                    break
        # Keep a bounded ownership set. One broad path may subsume its own
        # descendant, but never another concept's scope.
        smallest = sorted(found, key=lambda p: (p.count("/"), p))
        compressed = [p for p in smallest if not any(p == q or p.startswith(q + "/") for q in smallest if q != p)]
        if compressed and len(compressed) <= 12:
            candidates[concept] = compressed
    if not candidates or len(candidates) > 2:
        return order  # a host coordinator can inspect a more complex request
    groups = []
    for concept, paths in sorted(candidates.items()):
        groups.append({
            "id": concept,
            "task": "Trabalha apenas em " + concept + ". Pedido: " + request,
            "paths": paths,
        })
    for i, first in enumerate(groups):
        for second in groups[i+1:]:
            if any(a == b or a.startswith(b + "/") or b.startswith(a + "/")
                   for a in first["paths"] for b in second["paths"]):
                return order  # do not manufacture two independent agents
    return {**order, "work_items": groups}
