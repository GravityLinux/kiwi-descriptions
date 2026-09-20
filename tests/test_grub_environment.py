import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'root/usr/share/gravity-image-test/grub-environment.py'
spec = importlib.util.spec_from_file_location('grub_environment', SCRIPT)
grub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grub)


def block(values):
    data = grub.HEADER + ''.join(f'{k}={v}\n' for k, v in values.items()).encode()
    return data + b'#' * (1024 - len(data))


class EnvironmentTests(unittest.TestCase):
    def test_pointer_rejected(self):
        data = block({'env_block': '512+1', 'saved_entry': 'kernel'})
        with self.assertRaises(ValueError):
            grub.settings(data)
        self.assertEqual(grub.settings(data, True)['saved_entry'], 'kernel')

    def test_bad_environment_rejected(self):
        for data in (b'', b'#' * 1024, block({'saved_entry': 'a'})[:-1],
                     block({'saved_entry': 'a\nsaved_entry=b'})):
            with self.subTest(data=data[:30]), self.assertRaises(ValueError):
                grub.settings(data)

    def test_repair_preserves_settings_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'grubenv'
            expected = {'saved_entry': 'kernel', 'kernelopts': 'root=UUID=test nohlt',
                        'menu_auto_hide': '1', 'boot_success': '1', 'next_entry': ''}
            path.write_bytes(block(dict(expected, env_block='512+1')))

            def editenv(args, **kwargs):
                target = Path(args[1])
                if args[2] == 'create':
                    target.write_bytes(block({}))
                else:
                    target.write_bytes(block(dict(arg.split('=', 1) for arg in args[3:])))

            with patch.object(grub.subprocess, 'check_output', return_value='ext4\n'), \
                 patch.object(grub.subprocess, 'run', side_effect=editenv):
                grub.repair(path)
                grub.repair(path)
            self.assertEqual(grub.settings(path.read_bytes()), expected)
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)

    def test_wrong_filesystem_or_tool_failure_leaves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'grubenv'
            original = block({'env_block': '512+1'})
            path.write_bytes(original)
            with patch.object(grub.subprocess, 'check_output', return_value='btrfs\n'), \
                 self.assertRaises(ValueError):
                grub.repair(path)
            with patch.object(grub.subprocess, 'check_output', return_value='ext4\n'), \
                 patch.object(grub.subprocess, 'run', side_effect=RuntimeError('failed')), \
                 self.assertRaises(RuntimeError):
                grub.repair(path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_hook_is_post_install(self):
        root = SCRIPT.parents[4]
        self.assertIn('grub-environment.py', (root / 'edit_boot_install.sh').read_text())
        self.assertNotIn('grub-environment.py', (root / 'config.sh').read_text())
