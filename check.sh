#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python3 -m unittest discover -s tests -v
for script in build-image.sh config.sh post_bootstrap.sh pre_disk_sync.sh root/etc/fstab.script; do
    bash -n "$script"
done
git diff --check
