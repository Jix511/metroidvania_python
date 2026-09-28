import unittest

from systems.skill_data import (CLASS_SKILL_TREES, SKILL_CATEGORIES,
    UNIVERSAL_SKILLS)
from systems.skills import get_all_skills_for_class, get_skill_categories


class SkillDataTests(unittest.TestCase):
    def test_all_skill_definitions_are_loaded(self):
        total = len(UNIVERSAL_SKILLS) + sum(
            len(tree) for tree in CLASS_SKILL_TREES.values())

        self.assertEqual(total, 55)
        self.assertEqual(set(CLASS_SKILL_TREES),
                         {'warrior', 'rogue', 'mage', 'ranger', 'kitsune', 'reaper'})
        self.assertEqual(get_skill_categories(), SKILL_CATEGORIES)

    def test_each_class_receives_universal_and_class_skills(self):
        for class_id, tree in CLASS_SKILL_TREES.items():
            available = get_all_skills_for_class(class_id)
            self.assertEqual(len(available), len(UNIVERSAL_SKILLS) + len(tree))
            self.assertTrue(set(UNIVERSAL_SKILLS).issubset(available))
            self.assertTrue(set(tree).issubset(available))

    def test_requirements_reference_available_skills(self):
        for class_id in CLASS_SKILL_TREES:
            available = get_all_skills_for_class(class_id)
            for skill in available.values():
                self.assertTrue(set(skill['requires']).issubset(available))


if __name__ == '__main__':
    unittest.main()
