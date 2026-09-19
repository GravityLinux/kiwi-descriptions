#!/usr/bin/python3
"""Explicit modes for the Gravity overlay, independent of checkout umask.

Never recursively chmod the image: private system files must stay private.
Shared directories match Fedora's filesystem RPM; only our overlay is repaired.
"""
import argparse
from pathlib import Path
import stat

MODES = {
    'etc': 0o755,
    'usr': 0o755,
    'usr/share': 0o755,
    'usr/share/gravity-image-test': 0o755,
    'etc/fstab.script': 0o755,
    'usr/share/gravity-image-test/image-permissions.py': 0o644,
}


def validate(root, repair=False):
    errors = []
    for relative, expected in MODES.items():
        path = root / relative
        # KIWI consumes and removes this build-time hook during creation.
        if relative == 'etc/fstab.script' and not path.exists() and not path.is_symlink():
            continue
        # Reject symlinks in both the target and its ancestors before chmod.
        for component in [path, *path.parents]:
            if component == root:
                break
            if component.is_symlink():
                raise ValueError(f'Symlink in overlay path: {component}')
        actual = stat.S_IMODE(path.stat().st_mode)
        if repair:
            path.chmod(expected)
            actual = stat.S_IMODE(path.stat().st_mode)
        if actual != expected:
            errors.append(f'{relative}: {actual:04o}, expected {expected:04o}')
    if errors:
        raise ValueError('\n'.join(errors))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/'))
    parser.add_argument('--repair', action='store_true')
    args = parser.parse_args()
    validate(args.root, args.repair)
    print('PASS: Gravity overlay permissions')
