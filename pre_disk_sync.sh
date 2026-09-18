#!/bin/bash
set -euo pipefail
umask 022
# Fail closed before copying the tree into the disk image.
python3 /usr/share/gravity-image-test/image-permissions.py

# Remove kiwi leftovers we don't need
# https://github.com/OSInside/kiwi/issues/2343#issuecomment-1663427508
rm -f /boot/mbrid /config.bootoptions /config.partids

## Create /etc/X11/xorg.conf.d, see rhbz#2240159
mkdir -p /etc/X11/xorg.conf.d

exit 0
