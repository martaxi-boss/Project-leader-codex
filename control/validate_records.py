#!/usr/bin/env python3
import argparse
import hashlib
import json
import re
from datetime import datetime
from fnmatch import fnmatchcase
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASK_SCHEMA = ROOT / "task-authorization.schema.json"
TASK_SCHEMA_V1 = ROOT / "task-authorization.v1.schema.json"
TASK_SCHEMA_V2_LEGACY = ROOT / "task-authorization.v2.schema.json"
RESULT_SCHEMA = ROOT / "worker-result.schema.json"
RESULT_SCHEMA_V1 = ROOT / "worker-result.v1.schema.json"
CHECKPOINT_SCHEMA = ROOT / "recovery-checkpoint.schema.json"
RECOVERY_EVENT_SCHEMA = ROOT / "recovery-event.schema.json"
PROJECT_POLICY_SCHEMA = ROOT / "project-policy.schema.json"
STANDING_AUTHORITY_SCHEMA = ROOT / "standing-authority.schema.json"
TRANSITION_AUTH_SCHEMA = ROOT / "transition-authorization.schema.json"
TRANSITION_RESULT_SCHEMA = ROOT / "transition-result.schema.json"

CANONICAL_REQUIRED_CONTROLS = {
    "canonical_project_scope_must_cover_effect",
    "exact_target_and_revision_revalidated_before_consequential_transition",
    "required_ci_validation_and_evidence_must_pass",
    "supervisor_audits_before_and_after_consequential_transition",
    "recovery_guardian_verifies_ambiguous_writes_before_retry",
    "recovery_guardian_changes_strategy_after_repeated_failure",
    "transition_authorization_and_result_are_durable",
    "no_silent_scope_architecture_strategy_or_trust_boundary_expansion",
}

SUPPORTED_SCHEMA_KEYS = {
    "$schema", "$id", "title", "description", "type", "additionalProperties", "required",
    "properties", "const", "enum", "pattern", "minLength", "maxLength",
    "minimum", "minItems", "uniqueItems", "items", "format"
}

RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _json_equal(left, right):
    """JSON-semantic equality that never equates booleans with numbers."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if left is None or right is None:
        return left is None and right is None
    return left == right


def _matches_pattern(pattern, value):
    """Use whole-string matching for anchored identifier/path patterns."""
    if pattern.startswith("^") and pattern.endswith("$"):
        return re.fullmatch(pattern, value) is not None
    return re.search(pattern, value) is not None


def _load_schema(path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    _assert_supported_schema(schema)
    return schema

def _assert_supported_schema(schema, path="$schema"):
    unknown = set(schema) - SUPPORTED_SCHEMA_KEYS
    if unknown:
        raise ValueError(f"{path}: unsupported schema keywords: {', '.join(sorted(unknown))}")
    for name, child in schema.get("properties", {}).items():
        _assert_supported_schema(child, f"{path}.properties.{name}")
    items = schema.get("items")
    if isinstance(items, dict):
        _assert_supported_schema(items, f"{path}.items")

def _is_type(value, expected):
    mapping = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
    }
    if expected not in mapping:
        raise ValueError(f"unsupported JSON type: {expected}")
    return mapping[expected](value)

def _validate_datetime(value, path):
    if not isinstance(value, str):
        raise ValueError(f"{path}: date-time must be a string")
    if RFC3339_RE.fullmatch(value) is None:
        raise ValueError(f"{path}: date-time must use RFC3339 extended form")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{path}: invalid date-time") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{path}: date-time must include timezone")

def _validate(value, schema, path="$"):
    if "type" in schema:
        expected = schema["type"]
        options = expected if isinstance(expected, list) else [expected]
        if not any(_is_type(value, option) for option in options):
            raise ValueError(f"{path}: expected type {expected}")
    if "const" in schema and not _json_equal(value, schema["const"]):
        raise ValueError(f"{path}: expected constant {schema['const']!r}")
    if "enum" in schema and not any(_json_equal(value, item) for item in schema["enum"]):
        raise ValueError(f"{path}: value not in enum")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValueError(f"{path}: shorter than minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ValueError(f"{path}: longer than maxLength")
        if "pattern" in schema and not _matches_pattern(schema["pattern"], value):
            raise ValueError(f"{path}: does not match pattern")
        if schema.get("format") == "date-time":
            _validate_datetime(value, path)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"{path}: below minimum")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise ValueError(f"{path}: fewer than minItems")
        if schema.get("uniqueItems"):
            canonical = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
            if len(canonical) != len(set(canonical)):
                raise ValueError(f"{path}: duplicate items are not allowed")
        if "items" in schema:
            for index, item in enumerate(value):
                _validate(item, schema["items"], f"{path}[{index}]")
    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = [name for name in required if name not in value]
        if missing:
            raise ValueError(f"{path}: missing required fields: {', '.join(missing)}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(value) - set(properties)
            if unknown:
                raise ValueError(f"{path}: unknown fields: {', '.join(sorted(unknown))}")
        for name, child_schema in properties.items():
            if name in value:
                _validate(value[name], child_schema, f"{path}.{name}")

def _reject_duplicate_names(items, label):
    names = [item["name"] for item in items]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"duplicate {label} names are not allowed: {', '.join(duplicates)}")

def validate_project_policy(record):
    _validate(record, _load_schema(PROJECT_POLICY_SCHEMA))
    has_repository = "repository" in record
    has_default_branch = "default_branch" in record
    has_repository_mode = "repository_mode" in record
    has_default_branch_mode = "default_branch_mode" in record

    fixed_target = (
        has_repository
        and has_default_branch
        and not has_repository_mode
        and not has_default_branch_mode
    )
    dynamic_target = (
        not has_repository
        and not has_default_branch
        and has_repository_mode
        and has_default_branch_mode
        and record["repository_mode"] == "ACTIVE_TARGET"
        and record["default_branch_mode"] == "ACTIVE_TARGET"
    )
    if not (fixed_target or dynamic_target):
        raise ValueError(
            "project policy target mode must be either fixed repository+default_branch "
            "or both ACTIVE_TARGET mode fields, never partial or mixed"
        )
    for effect_name, effect_policy in (record.get("effect_policies") or {}).items():
        legacy = effect_policy.get("required_human_gates")
        current = effect_policy.get("required_transition_controls")
        if bool(legacy) == bool(current):
            raise ValueError(
                f"{effect_name}: project policy must declare exactly one of required_transition_controls or legacy required_human_gates"
            )
    return True


def validate_standing_authority(record):
    _validate(record, _load_schema(STANDING_AUTHORITY_SCHEMA))
    controls = record.get("required_controls")
    if set(controls or ()) != CANONICAL_REQUIRED_CONTROLS:
        missing = sorted(CANONICAL_REQUIRED_CONTROLS - set(controls or ()))
        unexpected = sorted(set(controls or ()) - CANONICAL_REQUIRED_CONTROLS)
        raise ValueError(
            "standing authority required_controls must equal the canonical invariant set; "
            f"missing={missing} unexpected={unexpected}"
        )
    return True


def validate_task(record):
    version = record.get("schema_version")
    if version == "1.0":
        schema = TASK_SCHEMA_V1
    elif version == "2.0" and "transition_controls" in record:
        schema = TASK_SCHEMA
    elif version == "2.0" and "human_gates" in record:
        schema = TASK_SCHEMA_V2_LEGACY
    elif version == "2.0":
        schema = TASK_SCHEMA
    else:
        raise ValueError(f"unsupported task schema_version: {version!r}")
    _validate(record, _load_schema(schema))
    if version == "2.0":
        policy = record["policy"]
        mode = policy.get("binding_mode")
        has_local = "base_sha" in policy
        has_central = "repository" in policy or "revision" in policy

        if mode is None:
            # Backward-compatible validation for historical v2 records created
            # before central-control policy binding existed.
            if not has_local or has_central:
                raise ValueError("legacy v2 task policy binding must use base_sha only")
            if policy["base_sha"] != record["starting_state"]["base_sha"]:
                raise ValueError("v2 task policy.base_sha must equal starting_state.base_sha")
        elif mode == "LOCAL_BASE_V1":
            if not has_local or has_central:
                raise ValueError("LOCAL_BASE_V1 requires base_sha and forbids repository/revision")
            if policy["base_sha"] != record["starting_state"]["base_sha"]:
                raise ValueError("LOCAL_BASE_V1 policy.base_sha must equal starting_state.base_sha")
        elif mode == "CENTRAL_CONTROL_V1":
            if has_local or not policy.get("repository") or not policy.get("revision"):
                raise ValueError("CENTRAL_CONTROL_V1 requires repository+revision and forbids base_sha")
        else:
            raise ValueError(f"unsupported v2 policy binding_mode: {mode!r}")

    return True

def validate_result(record):
    version = record.get("schema_version")
    if version == "1.0":
        schema = RESULT_SCHEMA_V1
    elif version == "2.0":
        schema = RESULT_SCHEMA
    else:
        raise ValueError(f"unsupported result schema_version: {version!r}")
    _validate(record, _load_schema(schema))
    _reject_duplicate_names(record["validation"], "validation")
    _reject_duplicate_names(record.get("ci", []), "CI")
    if bool(record.get("authorization_commit_sha")) != bool(record.get("authorization_sha256")):
        raise ValueError("authorization_commit_sha and authorization_sha256 must be provided together")
    if record["terminal_status"] in {"BLOCKED", "HUMAN_GATE", "STALE_EXECUTION_PACKET"}:
        if not record.get("residual_blockers"):
            raise ValueError(f"{record['terminal_status']} requires at least one residual_blocker")
    if record["terminal_status"] == "TERMINAL_SUCCESS":
        failed = [item["name"] for item in record["validation"] if item["status"] == "FAIL"]
        if failed:
            raise ValueError("terminal success cannot contain failed validation: " + ", ".join(failed))
        passed = [item["name"] for item in record["validation"] if item["status"] == "PASS"]
        if not passed:
            raise ValueError("terminal success requires at least one positive validation PASS")
        missing_evidence = [
            item["name"] for item in record["validation"]
            if item["status"] in {"PASS", "SKIPPED"} and not item.get("evidence")
        ]
        if missing_evidence:
            raise ValueError("terminal success requires evidence/justification for PASS or SKIPPED validation: " + ", ".join(missing_evidence))
        bad_ci = [item["name"] for item in record.get("ci", []) if item["status"] in {"FAILURE", "PENDING"}]
        if bad_ci:
            raise ValueError("terminal success cannot contain failing/pending CI: " + ", ".join(bad_ci))
    return True

def _require_named_status(items, required_names, expected_status, label):
    by_name = {item["name"]: item for item in items}
    missing = [name for name in required_names if name not in by_name]
    if missing:
        raise ValueError(f"required {label} missing: {', '.join(missing)}")
    wrong = [name for name in required_names if by_name[name]["status"] != expected_status]
    if wrong:
        raise ValueError(f"required {label} must be {expected_status}: " + ", ".join(wrong))

def validate_pair(task, result):
    validate_task(task)
    validate_result(result)
    if task["schema_version"] == "2.0" and result["schema_version"] != "2.0":
        raise ValueError("v2 task requires a v2 Worker Result")
    if task.get("integrity_mode") == "IMMUTABLE_AUTHORIZATION_V1":
        if not result.get("authorization_commit_sha") or not result.get("authorization_sha256"):
            raise ValueError("immutable authorization task requires authorization_commit_sha and authorization_sha256")
    checks = {
        "task_id": (task["task_id"], result["task_id"]),
        "repository": (task["repository"], result["repository"]),
        "effect_class": (task["effect_class"], result["effect_class"]),
        "branch": (task["starting_state"]["task_branch"], result["branch"]),
        "authorization_record": (f".project-leader/tasks/{task['task_id']}.json", result["authorization_record"]),
    }
    for name, (expected, actual) in checks.items():
        if expected != actual:
            raise ValueError(f"task/result mismatch for {name}: expected {expected!r}, got {actual!r}")
    expected_pr = task["starting_state"].get("pr_number")
    if expected_pr is not None and result.get("pr_number") != expected_pr:
        raise ValueError(f"task/result mismatch for pr_number: expected {expected_pr!r}, got {result.get('pr_number')!r}")
    if result["terminal_status"] == "TERMINAL_SUCCESS":
        _require_named_status(result["validation"], task.get("required_validation", []), "PASS", "validation")
        _require_named_status(result.get("ci", []), task.get("required_ci", []), "SUCCESS", "CI")
    return True

def _normalize_changed_path(path):
    if not isinstance(path, str):
        raise ValueError(f"invalid changed path: {path!r}")
    if (
        not path
        or path != path.strip()
        or "\\" in path
        or path.startswith("/")
        or ".." in Path(path).parts
    ):
        raise ValueError(f"invalid changed path: {path!r}")
    return path

def validate_scope(task, changed_files):
    validate_task(task)
    if not changed_files:
        raise ValueError("scope validation requires at least one changed file")
    patterns = task["mutation_scope"]
    normalized = [_normalize_changed_path(path) for path in changed_files]
    outside = [path for path in normalized if not any(fnmatchcase(path, pattern) for pattern in patterns)]
    if outside:
        raise ValueError("changed files outside authorized mutation_scope: " + ", ".join(sorted(outside)))
    return True

def validate_checkpoint(record):
    _validate(record, _load_schema(CHECKPOINT_SCHEMA))
    if record["attempt_count"] > 3:
        raise ValueError("recovery checkpoint attempt_count cannot exceed 3 for one action fingerprint")
    if record["identical_failure_count"] > 2:
        raise ValueError("recovery checkpoint identical_failure_count cannot exceed 2 before replan")
    if record["no_progress_iterations"] > 3:
        raise ValueError("recovery checkpoint no_progress_iterations cannot exceed 3")
    return True

def canonical_sha256(record):
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()

def validate_recovery_event(record):
    _validate(record, _load_schema(RECOVERY_EVENT_SCHEMA))
    if record["attempt_count"] > 3:
        raise ValueError("recovery event attempt_count cannot exceed 3")
    if record["identical_failure_count"] > 2:
        raise ValueError("recovery event identical_failure_count cannot exceed 2")
    if record["no_progress_iterations"] > 3:
        raise ValueError("recovery event no_progress_iterations cannot exceed 3")
    return True

def validate_recovery_journal(records):
    if not records:
        raise ValueError("recovery journal requires at least one event")
    ordered = sorted(records, key=lambda item: item["sequence"])
    task_id = ordered[0].get("task_id")
    repository = ordered[0].get("repository")
    terminal_seen = False
    fingerprint_state = {}

    for index, event in enumerate(ordered, start=1):
        validate_recovery_event(event)
        if event["sequence"] != index:
            raise ValueError(
                f"recovery journal sequence must be contiguous from 1; got {event['sequence']} at position {index}"
            )
        if event["task_id"] != task_id or event["repository"] != repository:
            raise ValueError("recovery journal cannot mix task_id or repository")
        if terminal_seen:
            raise ValueError("recovery journal cannot append after terminal event")

        if index == 1:
            if event["previous_event_sha256"] is not None:
                raise ValueError(
                    "first recovery event must have previous_event_sha256=null"
                )
        else:
            previous = ordered[index - 2]
            expected = canonical_sha256(previous)
            if event["previous_event_sha256"] != expected:
                raise ValueError("recovery journal hash chain mismatch")
            if event["strategy_generation"] < previous["strategy_generation"]:
                raise ValueError("recovery strategy_generation cannot decrease")
            if event["strategy_generation"] > previous["strategy_generation"]:
                if (
                    event["strategy_generation"]
                    != previous["strategy_generation"] + 1
                    or event["event"] != "REPLAN"
                ):
                    raise ValueError(
                        "strategy_generation may increase only by one on a REPLAN event"
                    )
            elif event["no_progress_iterations"] < previous["no_progress_iterations"]:
                raise ValueError(
                    "no_progress_iterations cannot decrease inside one strategy generation"
                )

        fingerprint = event.get("action_fingerprint")
        if fingerprint is not None:
            key = (event["strategy_generation"], fingerprint)
            prior = fingerprint_state.get(key)
            if prior is not None:
                if event["attempt_count"] < prior["attempt_count"]:
                    raise ValueError(
                        "attempt_count cannot decrease for a fingerprint within one strategy generation"
                    )
                if event["identical_failure_count"] < prior["identical_failure_count"]:
                    raise ValueError(
                        "identical_failure_count cannot decrease for a fingerprint within one strategy generation"
                    )
                if event["no_progress_iterations"] < prior["no_progress_iterations"]:
                    raise ValueError(
                        "no_progress_iterations cannot decrease for a fingerprint within one strategy generation"
                    )

            if event["event"] == "RETRY_AUTHORIZED":
                if prior is None:
                    if event["attempt_count"] != 1:
                        raise ValueError(
                            "first authorization for a new action fingerprint must use attempt_count=1"
                        )
                else:
                    if prior["event"] != "FAILURE_OBSERVED":
                        raise ValueError(
                            "RETRY_AUTHORIZED requires a preceding FAILURE_OBSERVED for an existing fingerprint"
                        )
                    expected_attempt = prior["attempt_count"] + 1
                    if event["attempt_count"] != expected_attempt:
                        raise ValueError(
                            "RETRY_AUTHORIZED must consume exactly one attempt from the same fingerprint budget"
                        )
                    if (
                        prior["attempt_count"] >= 3
                        or prior["identical_failure_count"] >= 2
                        or prior["no_progress_iterations"] >= 3
                    ):
                        raise ValueError(
                            "retry budget is exhausted; REPLAN is required before another retry"
                        )

            fingerprint_state[key] = {
                "event": event["event"],
                "attempt_count": event["attempt_count"],
                "identical_failure_count": event["identical_failure_count"],
                "no_progress_iterations": event["no_progress_iterations"],
            }

        if event["event"] in {"BLOCKED", "HUMAN_GATE", "COMPLETE"}:
            terminal_seen = True
    return True

def validate_transition_authorization(record):
    _validate(record, _load_schema(TRANSITION_AUTH_SCHEMA))
    if record["authority"]["binding_mode"] == "EXACT_REVISION_BOUND":
        target = record["target"]
        revision = target.get("revision")
        if not isinstance(revision, str) or not revision:
            raise ValueError("EXACT_REVISION_BOUND requires a non-empty target revision")
        if target.get("kind") in {"pull_request", "repository_branch", "git_commit"}:
            if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
                raise ValueError(
                    "Git EXACT_REVISION_BOUND targets require an exact 40-hex revision"
                )
        if target.get("kind") in {"pull_request", "repository_branch"}:
            base_revision = target.get("base_revision")
            if (
                not isinstance(base_revision, str)
                or re.fullmatch(r"[0-9a-f]{40}", base_revision) is None
            ):
                raise ValueError(
                    "Git EXACT_REVISION_BOUND targets require an exact 40-hex base_revision"
                )
    return True

def validate_transition_result(record):
    _validate(record, _load_schema(TRANSITION_RESULT_SCHEMA))
    status = record["terminal_status"]
    authorization_record = record["authorization_record"]
    if status in {"SUCCESS", "FAILURE", "NOT_EXECUTED"} and not authorization_record:
        raise ValueError(
            f"{status} transition requires a durable authorization_record"
        )
    if status in {"FAILURE", "NOT_EXECUTED"} and not record["residual_blockers"]:
        raise ValueError(
            f"{status} transition must record at least one residual_blocker"
        )
    if status == "HISTORICAL_OBSERVED":
        if authorization_record is not None:
            raise ValueError(
                "historical observed transition must not invent an authorization_record"
            )
        if not record["residual_blockers"]:
            raise ValueError(
                "historical observed transition must record the authorization-evidence gap"
            )
    return True

def validate_current_transition_result(record):
    """Apply current-state semantics to newly created or modified transition results.

    Historical records remain readable under their original contract; admission of
    new evidence uses this stricter state model.
    """
    validate_transition_result(record)
    if record["terminal_status"] == "SUCCESS" and record["residual_blockers"]:
        raise ValueError("successful transition cannot retain residual_blockers")
    return True


def validate_transition_pair(authorization, result):
    validate_transition_authorization(authorization)
    validate_transition_result(result)
    if result["terminal_status"] == "HISTORICAL_OBSERVED":
        raise ValueError("historical observed transitions are not authorization/result pairs")
    checks = {
        "transition_id": (authorization["transition_id"], result["transition_id"]),
        "task_id": (authorization["task_id"], result["task_id"]),
        "repository": (authorization["repository"], result["repository"]),
        "action": (authorization["action"], result["action"]),
        "target": (authorization["target"], result["target"]),
        "authorization_record": (
            f".project-leader/transitions/{authorization['transition_id']}.authorization.json",
            result["authorization_record"],
        ),
    }
    for name, (expected, actual) in checks.items():
        if expected != actual:
            raise ValueError(f"transition authorization/result mismatch for {name}: expected {expected!r}, got {actual!r}")
    return True

def validate_current_transition_pair(authorization, result):
    """Validate a newly created/modified pair, including temporal coherence.

    Historical pairs remain readable through validate_transition_pair because the
    repository contains known legacy timestamp inversions whose structural Git
    ancestry is correct. Current admission additionally requires the declared
    authorization creation time not to be later than the observed transition
    result time.
    """
    validate_transition_pair(authorization, result)
    created_at = datetime.fromisoformat(
        authorization["created_at"].replace("Z", "+00:00")
    )
    observed_at = datetime.fromisoformat(
        result["observed_at"].replace("Z", "+00:00")
    )
    if created_at > observed_at:
        raise ValueError(
            "current transition authorization created_at cannot be later than "
            "transition result observed_at"
        )
    return True


def validate_persisted_transition_result(record, repository_root=None):
    """Validate transition evidence and require durable authority for authorized outcomes."""
    validate_transition_result(record)
    if record["terminal_status"] == "HISTORICAL_OBSERVED":
        return True

    expected = (
        f".project-leader/transitions/{record['transition_id']}.authorization.json"
    )
    if record.get("authorization_record") != expected:
        raise ValueError(
            "authorized transition result must use the canonical authorization path"
        )
    root = Path(repository_root) if repository_root is not None else ROOT.parent
    auth_path = root / expected
    if not auth_path.is_file():
        raise ValueError(
            "authorized transition result requires the matching durable authorization file"
        )
    authorization = json.loads(auth_path.read_text(encoding="utf-8"))
    validate_transition_pair(authorization, record)
    return True

def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["policy","standing-authority","task","result","pair","scope","checkpoint","recovery-event","recovery-journal","transition-auth","transition-result","transition-result-current","transition-pair","transition-pair-current"])
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    if args.kind == "pair":
        if len(args.paths) != 2:
            parser.error("pair requires TASK_PATH RESULT_PATH")
        validate_pair(_read_json(args.paths[0]), _read_json(args.paths[1]))
    elif args.kind == "scope":
        if len(args.paths) < 2:
            parser.error("scope requires TASK_PATH CHANGED_FILE [CHANGED_FILE ...]")
        validate_scope(_read_json(args.paths[0]), args.paths[1:])
    elif args.kind == "recovery-journal":
        validate_recovery_journal([_read_json(path) for path in args.paths])
    elif args.kind in {"transition-pair", "transition-pair-current"}:
        if len(args.paths) != 2:
            parser.error(f"{args.kind} requires AUTHORIZATION_PATH RESULT_PATH")
        authorization = _read_json(args.paths[0])
        result = _read_json(args.paths[1])
        if args.kind == "transition-pair-current":
            validate_current_transition_pair(authorization, result)
        else:
            validate_transition_pair(authorization, result)
    else:
        if len(args.paths) != 1:
            parser.error(f"{args.kind} requires exactly one path")
        data = _read_json(args.paths[0])
        validators = {
            "policy": validate_project_policy,
            "standing-authority": validate_standing_authority,
            "task": validate_task,
            "result": validate_result,
            "checkpoint": validate_checkpoint,
            "recovery-event": validate_recovery_event,
            "transition-auth": validate_transition_authorization,
        }
        if args.kind == "transition-result":
            validate_persisted_transition_result(data)
        elif args.kind == "transition-result-current":
            validate_current_transition_result(data)
        else:
            validators[args.kind](data)
    print("VALID")

if __name__ == "__main__":
    main()
