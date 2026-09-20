#!/bin/bash
# KIWI calls this non-chrooted, AFTER final GRUB generation/installation.
# Arguments: raw disk image, final boot partition device. CWD: prepared root.
set -euo pipefail
umask 022
[[ $EUID == 0 && $# == 2 && -f $1 && -b $2 ]]
[[ $(blkid -s TYPE -o value "$2") == ext4 ]]
mountdir=$(mktemp -d /tmp/gravity-final-grub.XXXXXX)
cleanup() {
    if mountpoint -q "$mountdir"; then umount "$mountdir"; fi
    rmdir "$mountdir"
}
trap cleanup EXIT
mount -t ext4 -o rw "$2" "$mountdir"
python3 ./usr/share/gravity-image-test/grub-environment.py "$mountdir/grub2/grubenv"
sync -f "$mountdir/grub2/grubenv"
umount "$mountdir"
