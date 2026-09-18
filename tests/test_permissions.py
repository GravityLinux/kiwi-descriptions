import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'root/usr/share/gravity-image-test/image-permissions.py'
spec = importlib.util.spec_from_file_location('image_permissions', SCRIPT)
permissions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(permissions)


class PermissionTests(unittest.TestCase):
    def test_restrictive_overlay_repaired_without_opening_private_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path, mode in permissions.MODES.items():
                target = root / path
                if mode == 0o755 and '.' not in target.name:
                    target.mkdir(parents=True, exist_ok=True)
                    target.chmod(0o700)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.touch()
                    target.chmod(0o600)
            private = root / 'etc/shadow'
            private.touch(mode=0o600)
            with self.assertRaises(ValueError):
                permissions.validate(root)
            permissions.validate(root, repair=True)
            permissions.validate(root)
            (root / 'etc/fstab.script').unlink()
            permissions.validate(root)
            self.assertEqual(private.stat().st_mode & 0o777, 0o600)
            (root / 'usr').chmod(0o700)
            with self.assertRaises(ValueError):
                permissions.validate(root)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'private').mkdir(mode=0o700)
            (root / 'etc').symlink_to(root / 'private')
            with self.assertRaises(ValueError):
                permissions.validate(root, repair=True)
            self.assertEqual((root / 'private').stat().st_mode & 0o777, 0o700)
