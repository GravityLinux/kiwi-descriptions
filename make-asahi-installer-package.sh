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

[ "$#" -ne 2 ] && fail "usage: $0 <image> <package>"
image="$1"
package="$2"

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
pushd "$imagedir"
eval "$(sfdisk -ql "$imagename" | awk "NR>=2 { printf \"dd if=${imagename} of=${workdir}/%s skip=%s count=%s\\n\", \$1, \$2, \$4 }")"
popd

# build package
mkdir -p "${workdir}/package/esp"
fatcat "${workdir}/${imagename}1" -x "${workdir}/package/esp"
mv "${workdir}/${imagename}2" "${workdir}/package/boot.img"
mv "${workdir}/${imagename}3" "${workdir}/package/root.img"

pushd "${workdir}/package"
zip -r "${basedir}/${package}" .
popd
