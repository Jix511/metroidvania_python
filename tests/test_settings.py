import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from systems import settings


class SettingsTests(unittest.TestCase):
    def test_defaults_are_valid(self):
        self.assertTrue(settings.valid(settings.DEFAULTS))
        self.assertIn(tuple(settings.DEFAULTS['resolution']), settings.RESOLUTIONS)

    def test_invalid_resolution_and_volume_are_rejected(self):
        invalid_resolution = dict(settings.DEFAULTS, resolution=[111, 222])
        invalid_volume = dict(settings.DEFAULTS, master_volume=1.5)
        self.assertFalse(settings.valid(invalid_resolution))
        self.assertFalse(settings.valid(invalid_volume))

    def test_volume_adjustment_is_clamped(self):
        config = settings.normalize(settings.DEFAULTS)
        settings.adjust_volume(config, 'music_volume', 1.0)
        self.assertEqual(config['music_volume'], 1.0)
        settings.adjust_volume(config, 'music_volume', -2.0)
        self.assertEqual(config['music_volume'], 0.0)

    def test_resolution_cycles_through_supported_values(self):
        config = settings.normalize(settings.DEFAULTS)
        settings.cycle_resolution(config)
        self.assertEqual(tuple(config['resolution']), settings.RESOLUTIONS[1])

    def test_effects_quality_cycles_and_validates(self):
        config = settings.normalize(settings.DEFAULTS)
        self.assertEqual(config['effects_quality'], 'high')
        settings.cycle_effects_quality(config)
        self.assertEqual(config['effects_quality'], 'low')
        self.assertTrue(settings.valid(config))
        config['effects_quality'] = 'ultra'
        self.assertFalse(settings.valid(config))

    def test_legacy_settings_gain_default_effects_quality(self):
        legacy = dict(settings.DEFAULTS)
        legacy.pop('effects_quality')
        self.assertTrue(settings.valid(legacy))
        self.assertEqual(settings.normalize(legacy)['effects_quality'], 'high')

    def test_original_settings_file_gains_accessibility_defaults(self):
        legacy = {
            'resolution': [960, 640], 'fullscreen': False,
            'master_volume': 1.0, 'music_volume': 0.7, 'sfx_volume': 1.0,
        }
        self.assertTrue(settings.valid(legacy))
        normalized = settings.normalize(legacy)
        self.assertEqual(normalized['text_size'], 'normal')
        self.assertFalse(normalized['high_contrast'])
        self.assertEqual(normalized['screen_shake'], 1.0)

    def test_accessibility_cycles_are_valid(self):
        config = settings.normalize(settings.DEFAULTS)
        settings.cycle_text_size(config)
        settings.cycle_screen_shake(config)
        self.assertEqual(config['text_size'], 'large')
        self.assertEqual(config['screen_shake'], 0.5)
        self.assertTrue(settings.valid(config))

    def test_minimap_cycles_through_all_modes(self):
        config = settings.normalize(settings.DEFAULTS)
        seen = {config['minimap_mode']}
        for _ in range(2):
            settings.cycle_minimap_mode(config)
            seen.add(config['minimap_mode'])
        self.assertEqual({'full', 'compact', 'hidden'}, seen)
        self.assertTrue(settings.valid(config))

    def test_invalid_minimap_mode_is_rejected(self):
        self.assertFalse(settings.valid(dict(settings.DEFAULTS, minimap_mode='giant')))

    def test_invalid_accessibility_values_are_rejected(self):
        self.assertFalse(settings.valid(dict(settings.DEFAULTS, text_size='huge')))
        self.assertFalse(settings.valid(dict(settings.DEFAULTS, screen_shake=0.3)))
        self.assertFalse(settings.valid(dict(settings.DEFAULTS, reduced_motion='yes')))

    def test_settings_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'settings.json'
            config = settings.normalize(settings.DEFAULTS)
            config['music_volume'] = 0.4
            with patch.object(settings, 'SETTINGS_SAVE_PATH', path):
                self.assertTrue(settings.save(config))
                self.assertEqual(settings.load(), config)

    def test_corrupt_settings_fall_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'settings.json'
            path.write_text('{broken', encoding='utf-8')
            with patch.object(settings, 'SETTINGS_SAVE_PATH', path):
                self.assertEqual(settings.load(), settings.DEFAULTS)


if __name__ == '__main__':
    unittest.main()
