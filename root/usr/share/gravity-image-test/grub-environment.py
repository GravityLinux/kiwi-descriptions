#!/usr/bin/python3
"""Recreate a filesystem-backed GRUB environment on the final ext4 /boot."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

HEADER = b'# GRUB Environment Block\n'


def settings(data, allow_pointer=False):
    if len(data) != 1024 or not data.startswith(HEADER):
        raise ValueError('Expected a 1024-byte GRUB environment block')
    result = {}
    for line in data.decode('utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        key, separator, value = line.partition('=')
        if not separator or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key) or key in result:
            raise ValueError(f'Invalid/duplicate GRUB environment entry: {line!r}')
        if key == 'env_block' and not allow_pointer:
            raise ValueError('Raw env_block pointer is forbidden on the final ext4 boot filesystem')
        result[key] = value
    return result


def repair(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected a regular grubenv file')
    filesystem = subprocess.check_output(
        ['findmnt', '-n', '-o', 'FSTYPE', '-T', str(path)], text=True).strip()
    if filesystem != 'ext4':
        raise ValueError(f'Refusing to create grubenv on {filesystem!r}; final /boot must be ext4')
    # Read the file directly: grub2-editenv list may follow the invalid pointer.
    preserved = settings(path.read_bytes(), allow_pointer=True)
    preserved.pop('env_block', None)
    descriptor, temporary = tempfile.mkstemp(prefix='.grubenv-', dir=path.parent)
    os.close(descriptor)
    temporary = Path(temporary)
    try:
        subprocess.run(['grub2-editenv', str(temporary), 'create'], check=True)
        if preserved:
            subprocess.run(['grub2-editenv', str(temporary), 'set',
                            *(f'{key}={value}' for key, value in preserved.items())], check=True)
        if settings(temporary.read_bytes()) != preserved:
            raise ValueError('Replacement environment did not preserve all settings')
        # Preserve SELinux context and other xattrs already assigned by KIWI.
        shutil.copystat(path, temporary)
        temporary.chmod(0o644)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    print('PASS: filesystem-backed GRUB environment; settings preserved, env_block removed')


def check_image(path):
    debugfs = shutil.which('debugfs') or '/usr/sbin/debugfs'
    result = subprocess.run([debugfs, '-R', 'cat /grub2/grubenv', str(path)],
                            check=True, capture_output=True)
    # debugfs can return success for a missing file; the header/size check rejects it.
    settings(result.stdout)
    print('PASS: boot.img has a valid GRUB environment without raw-block indirection')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--check-image', action='store_true')
    args = parser.parse_args()
    if args.check_image:
        check_image(args.path)
    else:
        repair(args.path)
