import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('rotate', Path(__file__).with_name('tencent-headplane-key-rotate.py'))
rotate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rotate)


class RotationTest(unittest.TestCase):
    def test_success_replaces_credential_then_revokes_old_key(self):
        with tempfile.TemporaryDirectory() as directory:
            key, identifier = Path(directory)/'key', Path(directory)/'id'
            key.write_text('old-secret'); identifier.write_text('1')
            events = []
            def ready():
                self.assertEqual(key.read_text(), 'new-secret')
                events.append('ready')
            rotate.rotate_key(key, identifier, lambda: ('new-secret', '2'),
                              lambda: events.append('restart'), ready,
                              lambda value: events.append('revoke-'+value))
            self.assertEqual(identifier.read_text(), '2')
            self.assertEqual(events, ['restart', 'ready', 'revoke-1'])

    def test_failed_readiness_restores_both_files_and_revokes_new(self):
        with tempfile.TemporaryDirectory() as directory:
            key, identifier = Path(directory)/'key', Path(directory)/'id'
            key.write_text('old-secret'); identifier.write_text('1')
            events = []
            def reject(): raise RuntimeError('not ready')
            with self.assertRaises(RuntimeError):
                rotate.rotate_key(key, identifier, lambda: ('new-secret', '2'),
                                  lambda: events.append('restart'), reject,
                                  lambda value: events.append('revoke-'+value))
            self.assertEqual(key.read_text(), 'old-secret')
            self.assertEqual(identifier.read_text(), '1')
            self.assertEqual(events, ['restart', 'restart', 'revoke-2'])

    def test_failed_generation_leaves_active_credential_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            key, identifier = Path(directory)/'key', Path(directory)/'id'
            key.write_text('old-secret'); identifier.write_text('1')
            def reject(): raise RuntimeError('no new key')
            with self.assertRaises(RuntimeError):
                rotate.rotate_key(key, identifier, reject, lambda: None, lambda: None, lambda value: None)
            self.assertEqual(key.read_text(), 'old-secret')
            self.assertEqual(identifier.read_text(), '1')


if __name__ == '__main__':
    unittest.main()
