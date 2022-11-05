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

esp_volume_id="$(file "${workdir}/${imagename}1" | awk -v 'RS=,' '/serial number/ { print $3 }')"
esp_size="$(stat -c %s "${workdir}/${imagename}1")"
boot_size="$(stat -c %s "${workdir}/package/boot.img")"
# TODO: round up the size instead of hardcoding
truncate -s 10G "${workdir}/package/root.img"
root_size="$(stat -c %s "${workdir}/package/root.img")"

# boot picket icon
if [ ! -f fedora.icns ]; then
  wget https://pagure.io/fedora-logos/blob/master/f/bootloader/fedora.icns
fi
cp -p fedora.icns "${workdir}/package"

pushd "${workdir}/package" > /dev/null
zip -r "${basedir}/${package}" .
popd > /dev/null

cat > installer_data.json <<EOF
{
    "os_list": [
        {
            "name": "Fedora Rawide",
            "default_os_name": "Fedora Rawhide",
            "boot_object": "m1n1.bin",
            "next_object": "m1n1/boot.bin",
            "package": "${package}.zip",
            "icon": "fedora.icns",
            "supported_fw": ["12.3", "12.4"],
            "partitions": [
                {
                    "name": "EFI",
                    "type": "EFI",
                    "size": "${esp_size}B",
                    "format": "fat",
                    "volume_id": "${esp_volume_id}",
                    "copy_firmware": true,
                    "copy_installer_data": true,
                    "source": "esp"
                },
                {
                    "name": "Boot",
                    "type": "Linux",
                    "size": "${boot_size}B",
                    "image": "boot.img"
                },
                {
                    "name": "Root",
                    "type": "Linux",
                    "size": "${root_size}B",
                    "expand": true,
                    "image": "root.img"
                }
            ]
        }
    ]
}
EOF
