#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
umask 022
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
profile=${1:-Workstation-KDE-Test}
case "$profile" in
    Workstation-KDE|Workstation-KDE-Test) ;;
    *) echo "Use Workstation-KDE-Test or Workstation-KDE" >&2; exit 2 ;;
esac
[[ $(uname -m) == aarch64 ]] || { echo 'Run inside the Fedora AArch64 builder' >&2; exit 1; }
[[ $EUID == 0 ]] || { echo 'Run with sudo inside the builder VM' >&2; exit 1; }
output=${2:-"$PWD/outdir-$profile"}
[[ ! -e "$output" ]] || { echo "Output already exists: $output; choose a fresh directory" >&2; exit 1; }
install -Dm644 keys/RPM-GPG-KEY-gravity /usr/share/gravity-image-builder/RPM-GPG-KEY-gravity
python3 root/usr/share/gravity-image-test/image-permissions.py --root root --repair
exec kiwi-ng --debug --type=oem --profile="$profile" --color-output system build \
    --description "$PWD" --target-dir "$output"
