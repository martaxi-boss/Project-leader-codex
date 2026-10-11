from fnmatch import fnmatchcase

_GLOB_MAGIC = "*?["


def _normalize_scope_pattern(pattern):
    if not isinstance(pattern, str):
        raise ValueError(f"invalid mutation_scope pattern: {pattern!r}")
    if (
        not pattern
        or pattern != pattern.strip()
        or "\\" in pattern
        or pattern.startswith("/")
    ):
        raise ValueError(f"invalid mutation_scope pattern: {pattern!r}")
    parts = pattern.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"invalid mutation_scope pattern: {pattern!r}")
    return pattern


def _has_glob(pattern):
    return any(char in pattern for char in _GLOB_MAGIC)


def _literal_prefix(pattern):
    positions = [pattern.find(char) for char in _GLOB_MAGIC if char in pattern]
    return pattern[: min(positions)] if positions else pattern


def scope_pattern_is_bounded(pattern):
    """Return True only when a requested mutation scope has a literal boundary.

    Generic ACTIVE_TARGET policy must never accept semantic repository-wide
    aliases such as '*', '**', '***', or other patterns that start with glob
    syntax. Wildcard scopes must be rooted under an exact literal directory.
    """
    normalized = _normalize_scope_pattern(pattern)
    if not _has_glob(normalized):
        return True
    prefix = _literal_prefix(normalized)
    return bool(prefix) and prefix.endswith("/")


def scope_pattern_is_within(requested_pattern, allowed_pattern):
    requested = _normalize_scope_pattern(requested_pattern)
    allowed = _normalize_scope_pattern(allowed_pattern)

    if allowed == "**":
        return True

    if requested == allowed:
        return True

    if not _has_glob(requested):
        return fnmatchcase(requested, allowed)

    if not _has_glob(allowed):
        return False

    requested_prefix = _literal_prefix(requested)
    if allowed.endswith("/**") and not _has_glob(allowed[:-3]):
        return requested_prefix.startswith(allowed[:-2])
    if allowed.endswith("*") and not _has_glob(allowed[:-1]):
        return requested_prefix.startswith(allowed[:-1])
    return False
