import unittest

from systems import audio


class AudioFeedbackTests(unittest.TestCase):
    def test_every_class_has_attack_and_impact_identity(self):
        classes = {'warrior', 'rogue', 'ranger', 'mage', 'kitsune', 'reaper'}
        self.assertEqual(classes, set(audio.CLASS_ATTACK_SOUNDS))
        self.assertEqual(classes, set(audio.CLASS_IMPACT_SOUNDS))

    def test_reactions_have_distinct_sound(self):
        self.assertEqual(
            {'toxic_blast', 'thermal_shock', 'chain_lightning', 'shatter'},
            set(audio.REACTION_SOUNDS),
        )

    def test_all_biomes_and_refuge_have_ambience(self):
        self.assertEqual(
            {'meadow', 'caves', 'ruins', 'sanctum', 'peak', 'refuge'},
            set(audio.AMBIENT_SOUNDS),
        )

    def test_declared_feedback_sounds_are_built(self):
        built = set(audio._build())
        declared = set(audio.CLASS_IMPACT_SOUNDS.values())
        declared.update(name for names in audio.CLASS_ATTACK_SOUNDS.values() for name in names)
        declared.update(audio.REACTION_SOUNDS.values())
        declared.update(audio.AMBIENT_SOUNDS.values())
        declared.update({'critical', 'block', 'immune'})
        self.assertFalse(declared - built)


if __name__ == '__main__':
    unittest.main()
