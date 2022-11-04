#!/bin/sh

set -eu

fail() {
  echo $* >&2
  exit 1
}

requireCommands() {
  for cmd in $*; do
    if ! command -v $cmd &> /dev/null; then
      fail "Cannot find required command: $cmd"
    fi
  done
}

date=$(date +%Y%m%d)
image="${1:-outdir/Fedora-Asahi-Remix.aarch64-0.0.0.raw}"
package="${2:-fedora-rawhide-${date}}"

if [ ! -r "$image" ]; then
  fail "$image does not exist or cannot be read!"
fi

if [ -e "$package" ]; then
  fail "$package already exists, aborting"
fi

requireCommands sfdisk awk fatcat zip

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

basedir="$PWD"
imagename="$(basename "$image")"
imagedir="$(dirname "$image")"

# extract filesystems from disk image
pushd "$imagedir" > /dev/null
eval "$(sfdisk -ql "$imagename" | awk "NR>=2 { printf \"dd if=${imagename} of=${workdir}/%s skip=%s count=%s\\n\", \$1, \$2, \$4 }")"
popd > /dev/null

# build package
mkdir -p "${workdir}/package/esp"
fatcat "${workdir}/${imagename}1" -x "${workdir}/package/esp"
mv "${workdir}/${imagename}2" "${workdir}/package/boot.img"
mv "${workdir}/${imagename}3" "${workdir}/package/root.img"

pushd "${workdir}/package" > /dev/null
zip -r "${basedir}/${package}" .
popd > /dev/null

volume_id="$(file "${workdir}/${imagename}1" | awk -v 'RS=,' '/serial number/ { print $3 }')"
cat > installer_data.json <<EOF
{
    "os_list": [
        {
            "name": "Fedora Rawide",
            "default_os_name": "Fedora Rawhide",
            "boot_object": "m1n1.bin",
            "next_object": "m1n1/boot.bin",
            "package": "${package}.zip",
            "supported_fw": ["12.3", "12.4"],
            "partitions": [
                {
                    "name": "EFI",
                    "type": "EFI",
                    "size": "500MB",
                    "format": "fat",
                    "volume_id": "${volume_id}",
                    "copy_firmware": true,
                    "copy_installer_data": true,
                    "source": "esp"
                },
                {
                    "name": "Boot",
                    "type": "Linux",
                    "size": "1GB",
                    "image": "boot.img"
                },
                {
                    "name": "Root",
                    "type": "Linux",
                    "size": "15GB",
                    "expand": true,
                    "image": "root.img"
                }
            ]
        }
    ]
}
EOF
