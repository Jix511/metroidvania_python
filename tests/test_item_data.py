import unittest

from systems.item_data import (AFFIXES, BASE_ITEMS, ECONOMY, RARITIES,
    RARITY_ORDER, SLOTS, STARTING_KITS)
from systems.items import (buy_price, refresh_price, sell_price, starting_kit,
    upgrade_cost)


class ItemDataTests(unittest.TestCase):
    def test_expected_content_is_loaded(self):
        self.assertEqual(SLOTS, ['weapon', 'helmet', 'armor', 'boots', 'accessory'])
        self.assertEqual(len(AFFIXES), 14)
        self.assertEqual(sum(len(items) for items in BASE_ITEMS.values()), 19)
        self.assertEqual(RARITY_ORDER,
                         ['common', 'magic', 'rare', 'epic', 'legendary'])
        self.assertEqual(sum(rarity['weight'] for rarity in RARITIES.values()), 100)

    def test_economy_values_preserve_existing_prices(self):
        item = {
            'slot': 'weapon', 'level': 1, 'rarity': 'common',
            'stats': {'damage': 3},
        }

        self.assertEqual(buy_price(item), 60)
        self.assertEqual(sell_price(item), 20)
        self.assertEqual(refresh_price(1), 30)
        self.assertEqual(upgrade_cost(item), 30)
        self.assertEqual(ECONOMY['max_upgrade'], 8)

    def test_starting_kits_use_external_definitions(self):
        for class_id, definitions in STARTING_KITS.items():
            kit = starting_kit(class_id)
            self.assertEqual(len(kit), len(definitions))
            self.assertEqual([item['name'] for item in kit],
                             [entry['name'] for entry in definitions])
            self.assertEqual([item['stats'] for item in kit],
                             [entry['stats'] for entry in definitions])


if __name__ == '__main__':
    unittest.main()
