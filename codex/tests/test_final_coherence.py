"""Regressions for hidden tracked edits, effort drift and aggregate bounds."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from codex import dual, agent_policy


class CoherenceTests(unittest.TestCase):
    def test_hidden_tracked_edits_block_completion(self):
        for flag in ('--assume-unchanged', '--skip-worktree'):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                logdir = root / 'logs'
                logdir.mkdir()
                workspace = root / 'workspace'
                workspace.mkdir()
                root = workspace
                tmp = str(workspace)
                def git(*args):
                    subprocess.run(['git', '-C', tmp, *args], check=True, capture_output=True)
                git('init', '-q')
                git('config', 'user.name', 'Test')
                git('config', 'user.email', 'test@example.test')
                (root / 'outside.txt').write_text('original')
                (root / 'owned.txt').write_text('original')
                git('add', '.')
                git('commit', '-qm', 'baseline')
                def attack(*args, **kwargs):
                    git('update-index', flag, 'outside.txt')
                    (root / 'outside.txt').write_text('hidden attack')
                    (root / 'owned.txt').write_text('permitted edit')
                    self.assertNotIn('outside.txt', dual._changes(root))
                    return 0, json.dumps({'type': 'turn.completed'}) + '\n', '', None
                task = {'id': 'one', 'task': 'Implement scoped edits and validate',
                        'paths': ['owned.txt'], 'selected_effort': 'medium'}
                with mock.patch.object(dual, '_invoke_codex', side_effect=attack), mock.patch.object(dual, '_prompt', return_value='scoped'):
                    result = dual._worker(task, root, logdir, 30)
                self.assertEqual(result['status'], 'scope_violation')
                self.assertIn('outside.txt', result['out_of_scope'])

    def test_complex_effort_matches_planning_selection_and_execution(self):
        registry = agent_policy.load_registry()
        for provider in registry['providers']:
            for model in provider['models']:
                model['quality_tier'] = 5
        for prompt in ('Diagnose complex regression and validate the fix',
                       'Investigar causa raiz e validar a correção',
                       'Fix credential handling and validate the result',
                       'Perform irreversible migration and validate results'):
            item = {'id': 'one', 'task': prompt, 'paths': ['src/core'], 'reasoning_effort': 'auto'}
            with self.subTest(prompt=prompt):
                p = agent_policy.plan({'request': prompt, 'target_repository': 'martaxi-boss/Project-leader-codex', 'work_items': [item]}, registry)
                self.assertEqual(p['phase_plan'][0]['reasoning_effort'], 'high')
                self.assertEqual(p['tasks'][0]['selection']['reasoning_effort'], 'high')
                self.assertEqual(dual.effort(item), 'high')
                for level in ('low', 'medium'):
                    with self.assertRaises(agent_policy.RoutingError):
                        agent_policy._classify_effort({**item, 'reasoning_effort': level})

    def test_launch_rejects_stale_medium_selection_for_complex_work(self):
        task = {'id': 'one', 'task': 'Diagnose complex regression and validate the fix',
                'paths': ['src/core'], 'selected_effort': 'medium'}
        with mock.patch.object(dual, '_invoke_codex') as invoke:
            with self.assertRaisesRegex(dual.PlanError, 'requires at least high'):
                dual._worker(task, Path('/unused'), Path('/unused'), 30)
        invoke.assert_not_called()

    def test_aggregate_path_bounds_fail_closed_in_all_modes(self):
        for mode in ('single', 'serial', 'parallel', 'auto'):
            rows = [{'id': f'item-{i}', 'task': 'Implement module and run integration tests',
                     'paths': [f'src/module-{i}/file-{j}' for j in range(20)]}
                    for i in range(4)]
            if mode == 'serial':
                for i in range(1, 4):
                    rows[i]['depends_on'] = [rows[i-1]['id']]
            with self.subTest(mode=mode), self.assertRaisesRegex(agent_policy.RoutingError, '20'):
                agent_policy.plan({'request': 'Implement bounded modules and validate tests', 'target_repository': 'martaxi-boss/Project-leader-codex', 'work_items': rows, 'preference': mode})

    def test_duplicate_aggregate_paths_count_once_and_preserve_sequence(self):
        paths = [f'src/file-{j}' for j in range(20)]
        rows = [{'id': f'item-{i}', 'task': f'Implement step {i} and validate tests', 'paths': paths,
                 'depends_on': ['item-0'] if i else []} for i in range(2)]
        p = agent_policy.plan({'request': 'Implement bounded sequential steps and validate tests', 'target_repository': 'martaxi-boss/Project-leader-codex', 'work_items': rows, 'preference': 'single'})
        self.assertEqual(p['tasks'][0]['paths'], paths)
        self.assertEqual(p['phase_plan'][1]['depends_on'], ['item-0'])
