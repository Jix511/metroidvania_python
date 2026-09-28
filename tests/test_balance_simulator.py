import json
import tempfile
import unittest
from pathlib import Path

from tools.balance_simulator import (build_report, enemy_metrics, main,
    render_text, xp_curve)


class BalanceSimulatorTests(unittest.TestCase):
    def test_enemy_ng_scaling_matches_game_formula(self):
        base = enemy_metrics('goblin', 0)
        ng_one = enemy_metrics('goblin', 1)

        self.assertEqual(base['health'], 40)
        self.assertEqual(base['damage'], 10)
        self.assertEqual(ng_one['health'], 64)
        self.assertEqual(ng_one['damage'], 14)
        self.assertEqual(ng_one['xp'], 45)

    def test_xp_curve_matches_level_growth(self):
        curve = xp_curve(4)

        self.assertEqual([row['required'] for row in curve], [100, 140, 196])
        self.assertEqual(curve[-1]['total'], 436)

    def test_report_contains_every_balance_section(self):
        report = build_report(player_level=5, ng_cycle=1)

        self.assertEqual(set(report['classes']),
                         {'warrior', 'rogue', 'mage', 'ranger', 'kitsune',
                          'reaper'})
        self.assertEqual(len(report['enemies']), 9)
        self.assertEqual(len(report['bosses']), 3)
        self.assertIn('campaign_rewards', report['progression'])
        self.assertIn(5, report['item_samples'])
        self.assertIn('SIMULADOR DE BALANCE', render_text(report))

    def test_cli_can_write_json_report(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'balance.json'

            result = main(['--level', '3', '--ng', '1', '--format', 'json',
                           '--output', str(output)])
            document = json.loads(output.read_text(encoding='utf-8'))

        self.assertEqual(result, 0)
        self.assertEqual(document['parameters'], {'player_level': 3, 'ng_cycle': 1})


if __name__ == '__main__':
    unittest.main()
