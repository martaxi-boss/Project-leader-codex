"""Offline Codex Cloud -> verified Owner Issue -> independent VPS Coordinator tests."""
import json
import subprocess
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace

from codex import owner_coordinator_ingress as ingress

REPO = "martaxi-boss/Project-leader-codex"
TASK = "Corrige a palavra ultimo para último no README_CODEX.md do Project-leader-codex."
NONCE = "abcdef0123456789"
LATEST_SHA = "a" * 40


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
        elif (method, path) == ("GET", "repos/martaxi-boss/Project-leader-codex/branches/main"):
            payload = {"commit": {"sha": LATEST_SHA}}
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

    def test_long_owner_order_keeps_full_text_under_existing_byte_bound(self):
        # Full Owner acceptance criteria may exceed the historical 3700-char
        # cap; preserving them is safer than silent truncation or hand editing.
        long_task = "Corrigir Live TV, Movies e Series sem estragar VPN. " + (
            "Preservar velocidade, login e testes Android. " * 110)
        self.assertGreater(len(long_task), 3700)
        expected = "TARGET_REPOSITORY=" + REPO + "\n\n" + long_task.strip()
        self.assertLessEqual(len(expected.encode("utf-8")), 8000)
        self.assertEqual(ingress.validate_order(REPO, long_task), expected)

    def test_long_utf8_owner_order_still_obeys_byte_limit(self):
        over_budget = "Corrigir categorias Movies e Series. " + ("ç" * 5000)
        self.assertLess(len(over_budget), 8000)
        with self.assertRaisesRegex(ingress.IngressBlocked,
                                    "ORDER_ENVELOPE_UNVERIFIED"):
            ingress.validate_order(REPO, over_budget)

    def test_read_only_owner_identity_diagnostic_never_writes(self):
        api = FakeGitHub()
        ingress.verify_owner_read_access(REPO, runner=api)
        self.assertEqual(api.posts, 0)
        self.assertEqual([x[0][3] for x in api.calls], ["GET", "GET"])
        wrong = FakeGitHub(login="github-actions[bot]")
        with self.assertRaisesRegex(ingress.IngressBlocked, "AUTHENTICATED_AS_OWNER"):
            ingress.verify_owner_read_access(REPO, runner=wrong)
        self.assertEqual(wrong.posts, 0)

    def test_cli_check_auth_is_diagnostic_not_a_dispatch(self):
        sink = StringIO()
        with patch.object(ingress, "verify_owner_read_access") as verified, \
                patch.object(ingress, "verify_cloud_checkout_current") as current:
            with redirect_stdout(sink):
                status = ingress.main(["--target", REPO, "--check-auth"])
        self.assertEqual(status, 0)
        verified.assert_called_once_with(REPO)
        self.assertIn("ISSUES_WRITE_UNTESTED", sink.getvalue())
        self.assertNotIn("SUBMITTED_PENDING_WORKFLOW", sink.getvalue())

    def test_cloud_checkout_accepts_exact_main_and_descendant_only(self):
        api = FakeGitHub()
        commands = []

        def git_same(argv, **kwargs):
            commands.append(argv[:])
            self.assertEqual(argv[:3], ["git", "-C", "/safe-checkout"])
            self.assertTrue(kwargs["capture_output"] and kwargs["text"])
            self.assertFalse(kwargs["check"])
            self.assertEqual(argv[3:], ["rev-parse", "HEAD"])
            return SimpleNamespace(returncode=0, stdout=LATEST_SHA + "\n")
        ingress.verify_cloud_checkout_current(
            gh_runner=api, git_runner=git_same, checkout=Path("/safe-checkout"))
        self.assertEqual(len(commands), 1)
        self.assertEqual([x[0][3] for x in api.calls], ["GET"])
        self.assertEqual(api.posts, 0)

        calls = []
        def git_descendant(argv, **kwargs):
            calls.append(argv[3:])
            if argv[3:] == ["rev-parse", "HEAD"]:
                return SimpleNamespace(returncode=0, stdout="b" * 40 + "\n")
            if argv[3:] == ["merge-base", "--is-ancestor", LATEST_SHA, "HEAD"]:
                return SimpleNamespace(returncode=0, stdout="")
            raise AssertionError("Unexpected Git action")
        ingress.verify_cloud_checkout_current(
            gh_runner=FakeGitHub(), git_runner=git_descendant,
            checkout=Path("/safe-checkout"))
        self.assertEqual(len(calls), 2)

    def test_cloud_checkout_fails_closed_on_stale_local_snapshot(self):
        api = FakeGitHub()
        calls = []
        def stale_git(argv, **kwargs):
            calls.append(argv[3:])
            if argv[3:] == ["rev-parse", "HEAD"]:
                return SimpleNamespace(returncode=0, stdout="b" * 40 + "\n")
            if argv[3:] == ["merge-base", "--is-ancestor", LATEST_SHA, "HEAD"]:
                return SimpleNamespace(returncode=1, stdout="")
            raise AssertionError("Unexpected Git action")
        with self.assertRaisesRegex(
                ingress.IngressBlocked, "CODEX_CLOUD_CHECKOUT_STALE_MAIN_NOT_CONTAINED"):
            ingress.verify_cloud_checkout_current(
                gh_runner=api, git_runner=stale_git,
                checkout=Path("/safe-checkout"))
        self.assertEqual(len(calls), 2)
        self.assertEqual(api.posts, 0)

    def test_cloud_checkout_rejects_unverifiable_git_without_fetch_or_reset(self):
        api = FakeGitHub()
        def no_git(*args, **kwargs):
            raise FileNotFoundError("git")
        with self.assertRaisesRegex(
                ingress.IngressBlocked, "CODEX_CLOUD_CHECKOUT_UNVERIFIED"):
            ingress.verify_cloud_checkout_current(
                gh_runner=api, git_runner=no_git,
                checkout=Path("/safe-checkout"))
        self.assertEqual(api.posts, 0)

    def test_cli_stale_snapshot_prevents_owner_issue_submission(self):
        from contextlib import redirect_stderr
        sink = StringIO()
        with patch.object(ingress, "verify_cloud_checkout_current",
                          side_effect=ingress.IngressBlocked(
                              "CODEX_CLOUD_CHECKOUT_STALE_MAIN_NOT_CONTAINED"
                          )) as fresh, \
                patch.object(ingress, "submit_owner_order") as submit, \
                redirect_stderr(sink):
            code = ingress.main(["--target", REPO, "--task", TASK])
        self.assertEqual(code, 2)
        fresh.assert_called_once_with()
        submit.assert_not_called()
        self.assertIn("CHECKOUT_STALE", sink.getvalue())

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

    def test_cloud_owner_direct_execution_is_independent_default(self):
        root = Path(__file__).resolve().parents[2]
        guide = (root / "AGENTS.md").read_text(encoding="utf-8")
        policy = (root / "CODEX_COORDINATION.md").read_text(encoding="utf-8")
        self.assertIn("direct Cloud execution request by default", guide)
        self.assertIn("**Codex Cloud direct Owner task (default for Cloud)**", policy)
        self.assertIn("screenshots, photographs, documents or examples", guide)
        self.assertIn("not automatically relay this instruction to the VPS", guide)
        self.assertIn("implement, test, correct", guide)
        self.assertIn("Owner-selected Codex Cloud task can execute there", guide)
        self.assertIn("VPS (unchanged and independent)", policy)
        self.assertIn("The **only Supervisor**", policy)

    def test_chatgpt_vps_and_cloud_direct_are_separate_authorized_routes(self):
        root = Path(__file__).resolve().parents[2]
        guide = (root / "AGENTS.md").read_text(encoding="utf-8")
        policy = (root / "CODEX_COORDINATION.md").read_text(encoding="utf-8")
        self.assertIn("The VPS entry point", guide)
        self.assertIn("An Owner order issued in an ordinary **ChatGPT chat**", guide)
        self.assertIn("goes to the **existing VPS Codex Coordinator**", guide)
        self.assertIn("Owner orders issued to the VPS", guide)
        self.assertIn("explicitly request **VPS delegation**", guide)
        self.assertIn("codex.owner_coordinator_ingress", guide)
        self.assertIn("must never relay its own task back", policy)
        self.assertIn("only Supervisor", guide)
        self.assertNotIn("the relay is the first substantive", guide)
        self.assertNotIn("stop local work: the VPS Coordinator owns", guide)

    def test_cloud_private_media_cannot_silently_become_text_only_order(self):
        root = Path(__file__).resolve().parents[2]
        guide = (root / "AGENTS.md").read_text(encoding="utf-8")
        policy = (root / "CODEX_COORDINATION.md").read_text(encoding="utf-8")
        self.assertIn("An attachment", guide)
        self.assertIn("NOT automatically a file on the VPS", guide)
        self.assertIn("must NOT silently become a text-only order", guide)
        self.assertIn("verified private media path", guide)
        self.assertIn("never transmit", policy)
        self.assertIn("do not create a second supervisor", policy.lower())
        self.assertIn("Do not create a\nCloud Supervisor", guide)

    def test_vps_relay_identity_and_stale_cloud_checks_remain_intact(self):
        # This routing change must not weaken the existing optional text-only relay.
        source = (Path(__file__).resolve().parents[1]
                  / "owner_coordinator_ingress.py").read_text(encoding="utf-8")
        self.assertIn("verify_owner_read_access(target", source)
        self.assertIn("verify_cloud_checkout_current()", source)
        self.assertIn("GITHUB_AUTH_OR_WRITE_NOT_VERIFIED", source)
        self.assertIn("CODEX_CLOUD_CHECKOUT_STALE_MAIN_NOT_CONTAINED", source)


if __name__ == "__main__":
    unittest.main()
