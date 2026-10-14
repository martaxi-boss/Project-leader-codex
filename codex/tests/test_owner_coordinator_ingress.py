"""Offline Codex Cloud -> verified Owner Issue -> independent VPS Coordinator tests."""
import json
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace

from codex import owner_coordinator_ingress as ingress

REPO = "martaxi-boss/Project-leader-codex"
TASK = "Corrige a palavra ultimo para último no README_CODEX.md do Project-leader-codex."
NONCE = "abcdef0123456789"


class FakeGitHub:
    def __init__(self, login="martaxi-boss", owner="martaxi-boss",
                 private=False, archived=False, branch="main", writer="martaxi-boss",
                 fail_on=None, existing=None, ambiguous_commit=False):
        self.login = login
        self.owner = owner
        self.private = private
        self.archived = archived
        self.branch = branch
        self.writer = writer
        self.fail_on = fail_on
        self.existing = list(existing or [])
        self.ambiguous_commit = ambiguous_commit
        self.calls = []
        self.posts = 0

    def __call__(self, argv, *, input=None, text=True, capture_output=True,
                 timeout=None, check=False):
        assert argv[:4] == ["gh", "api", "--method", argv[3]]
        assert text and capture_output and not check
        assert 0 < timeout <= 30
        self.calls.append((argv[:], input))
        method, path = argv[3], argv[4]
        if (method, path) == self.fail_on:
            return SimpleNamespace(returncode=1, stdout="", stderr="REDACTED")
        if (method, path) == ("GET", "user"):
            payload = {"login": self.login}
        elif (method, path) == ("GET", "repos/" + REPO):
            payload = {"full_name": REPO, "owner": {"login": self.owner},
                       "private": self.private, "archived": self.archived,
                       "default_branch": self.branch}
        elif method == "GET" and path.startswith("repos/martaxi-boss/VPS/issues?state=open&per_page=100&page="):
            page = int(path.rsplit("=", 1)[1])
            payload = self.existing[(page - 1) * 100:page * 100]
        elif (method, path) == ("POST", "repos/martaxi-boss/VPS/issues"):
            self.posts += 1
            assert argv[-2:] == ["--input", "-"]
            sent = json.loads(input)
            assert sent["body"] == "TARGET_REPOSITORY=" + REPO + "\n\n" + TASK
            assert sent["title"].startswith("[coordinator run] Codex Cloud ")
            payload = {"number": 21501, "title": sent["title"],
                       "body": sent["body"], "user": {"login": self.writer}}
            if self.ambiguous_commit:
                self.existing.append(payload)
                return SimpleNamespace(returncode=1, stdout="", stderr="REDACTED")
        else:
            raise AssertionError("Unexpected gh call " + repr(argv))
        return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")


class CloudOwnerIngressTests(unittest.TestCase):
    def test_relay_creates_only_one_owner_issue_not_second_coordinator(self):
        api = FakeGitHub()
        number = ingress.submit_owner_order(REPO, TASK, runner=api, unique_id=NONCE)
        self.assertEqual(number, 21501)
        self.assertEqual(api.posts, 1)
        self.assertEqual([x[0][3] for x in api.calls], ["GET", "GET", "GET", "POST"])
        self.assertIn("TARGET_REPOSITORY=", api.calls[3][1])
        self.assertFalse(any("codex exec" in repr(x) for x in api.calls))

    def test_rejects_other_owner_ambiguous_name_and_public_secrets(self):
        invalid = [
            ("other-owner/app", TASK),
            ("martaxi-boss/app/../../VPS", TASK),
            ("martaxi-boss/repo.git", TASK),
            (REPO, "Corrige password=ABCD1234EFGH5678 no README"),
            (REPO, "Corrige sk-testsecret012345678901234"),
            (REPO, "Corrige\nNova linha\u0000"),
            (REPO, "Faz"),
        ]
        for target, task in invalid:
            with self.subTest(target=target, task=task[:22]):
                with self.assertRaises(ingress.IngressBlocked):
                    ingress.submit_owner_order(target, task, runner=FakeGitHub(),
                                               unique_id=NONCE)

    def test_cloud_identity_required_before_write(self):
        api = FakeGitHub(login="github-actions[bot]")
        with self.assertRaisesRegex(ingress.IngressBlocked, "AUTHENTICATED_AS_OWNER"):
            ingress.submit_owner_order(REPO, TASK, runner=api, unique_id=NONCE)
        self.assertEqual(api.posts, 0)
        self.assertEqual(len(api.calls), 1)

    def test_invalid_or_nonpublic_target_rejected(self):
        for opts in ({"owner": "other-owner"}, {"private": True},
                     {"archived": True}, {"branch": "develop"}):
            api = FakeGitHub(**opts)
            with self.subTest(opts=opts):
                with self.assertRaises(ingress.IngressBlocked):
                    ingress.submit_owner_order(REPO, TASK, runner=api,
                                               unique_id=NONCE)
            self.assertEqual(api.posts, 0)

    def test_issue_must_be_owner_authored_and_exact(self):
        api = FakeGitHub(writer="github-actions[bot]")
        with self.assertRaisesRegex(ingress.IngressBlocked, "CREATION_UNVERIFIED"):
            ingress.submit_owner_order(REPO, TASK, runner=api, unique_id=NONCE)
        self.assertEqual(api.posts, 1)

    def test_failure_does_not_retry_ambiguous_issue_write(self):
        api = FakeGitHub(fail_on=("POST", "repos/martaxi-boss/VPS/issues"))
        with self.assertRaisesRegex(ingress.IngressBlocked, "GITHUB_AUTH_OR_WRITE"):
            ingress.submit_owner_order(REPO, TASK, runner=api, unique_id=NONCE)
        self.assertEqual(len([x for x in api.calls if x[0][3] == "POST"]), 1)

    def test_gh_not_available_has_no_unsafe_fallback(self):
        def no_gh(*_args, **_kwargs):
            raise FileNotFoundError("gh")
        with self.assertRaisesRegex(ingress.IngressBlocked, "GITHUB_CLI_UNAVAILABLE"):
            ingress.submit_owner_order(REPO, TASK, runner=no_gh, unique_id=NONCE)

    def test_existing_open_owner_order_is_reused(self):
        prior = {"number": 445, "title": "[coordinator run] Codex Cloud " + NONCE,
                 "body": "TARGET_REPOSITORY=" + REPO + "\n\n" + TASK,
                 "user": {"login": "martaxi-boss"}}
        api = FakeGitHub(existing=[prior])
        number = ingress.submit_owner_order(REPO, TASK, runner=api, unique_id=NONCE)
        self.assertEqual(number, 445)
        self.assertEqual(api.posts, 0)

    def test_ambiguous_post_is_reconciled_not_replayed(self):
        api = FakeGitHub(ambiguous_commit=True)
        number = ingress.submit_owner_order(REPO, TASK, runner=api, unique_id=NONCE)
        self.assertEqual(number, 21501)
        self.assertEqual(api.posts, 1)
        self.assertEqual([x[0][3] for x in api.calls],
                         ["GET", "GET", "GET", "POST", "GET"])

    def test_open_owner_order_reconciliation_checks_next_page(self):
        prior = {"number": 772, "title": "[coordinator run] Codex Cloud " + NONCE,
                 "body": "TARGET_REPOSITORY=" + REPO + "\n\n" + TASK,
                 "user": {"login": "martaxi-boss"}}
        filler = [{"number": n + 1, "title": "Unrelated issue",
                   "body": "", "user": {"login": "martaxi-boss"}}
                  for n in range(100)]
        api = FakeGitHub(existing=filler + [prior])
        self.assertEqual(
            ingress.submit_owner_order(REPO, TASK, runner=api, unique_id=NONCE), 772)
        self.assertEqual(api.posts, 0)

    def test_foreign_issue_collision_fails_closed(self):
        foreign = {"number": 445, "title": "[coordinator run] Codex Cloud " + NONCE,
                   "body": "TARGET_REPOSITORY=" + REPO + "\n\n" + TASK,
                   "user": {"login": "someone-else"}}
        api = FakeGitHub(existing=[foreign])
        with self.assertRaisesRegex(ingress.IngressBlocked, "COLLISION"):
            ingress.submit_owner_order(REPO, TASK, runner=api, unique_id=NONCE)
        self.assertEqual(api.posts, 0)

    def test_deterministic_nonce_for_same_owner_order(self):
        import hashlib
        nonce = hashlib.sha256((REPO + "\\0" + TASK).encode("utf-8")).hexdigest()[:16]
        api = FakeGitHub()
        number = ingress.submit_owner_order(REPO, TASK, runner=api)
        self.assertEqual(number, 21501)
        self.assertEqual(api.posts, 1)
        self.assertIn(nonce, api.calls[-1][1])

    def test_cloud_owner_ingress_precedes_all_worker_bootstrap(self):
        guide = (Path(__file__).resolve().parents[2] / "AGENTS.md").read_text(
            encoding="utf-8")
        first = guide.index("the relay is the first substantive")
        worker = guide.index("When a **verified VPS Coordinator-dispatched worker**")
        self.assertLess(first, worker)
        self.assertIn("Do not run the full Project Leader", guide)
        self.assertIn("stop local work", guide)
        self.assertIn("Never substitute local Codex execution", guide)
        self.assertIn("GH", guide.upper())  # GitHub Owner identity remains mandatory

    def test_worker_guidance_cannot_recursive_dispatch(self):
        root = Path(__file__).resolve().parents[2]
        guide = (root / "AGENTS.md").read_text(encoding="utf-8")
        policy = (root / "CODEX_COORDINATION.md").read_text(encoding="utf-8")
        self.assertIn("Codex Cloud chat", guide)
        self.assertIn("codex.owner_coordinator_ingress", guide)
        self.assertIn("A Codex worker already", guide)
        self.assertIn("skip this", guide)
        self.assertIn("must never relay its own task back", policy)
        self.assertIn("Project Leader", guide)
        self.assertIn("independent Coordinator", guide)


if __name__ == "__main__":
    unittest.main()
