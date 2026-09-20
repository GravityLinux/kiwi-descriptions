# Gravity Linux KIWI descriptions

Fedora 44 / AArch64 / KDE recipe for the T8132 M4 Mac mini (j773g).
See NOTICE for source attribution and COPYING for the license.

## Profiles

- `Workstation-KDE-Test`: temporary hardware bring-up image using staging RPMs.
- `Workstation-KDE`: eventual release profile using published RPMs. Not release-ready.

Both profiles use the kernel-protected J773g speaker driver with PipeWire and
WirePlumber. They select platform subpackages directly to avoid the umbrella's
remaining legacy `asahi-audio` dependency, and exclude the old DSP/daemon stack.
`alsa-ucm-asahi` remains available for other ALSA devices; no legacy speaker DSP
is enabled. The recipe requires built-in J773g protection, TAS2764 and Apple MCA
in every installed 16K kernel config. It removes the previous recipe's explicit
audio blacklist and daemon mask, then regenerates portable initramfs images.
This configuration enables testing; it is not hardware audio validation.

The test profile uses COPR's fedora-44-aarch64-devel staging repository because
manual publication is enabled and the public repository is currently empty.
The installed test system also uses staging. Never distribute this profile as
a final release. The release profile uses the published repository.

Both profiles retain Fedora's base and updates repositories, RPM signature
checking, and the checked-in Gravity COPR signing key. No upstream hardware COPRs are used
by the active recipe. Hardware ABI names, apple_m1, m1n1/boot.bin, and Fedora's
GRUB/ESP paths are deliberately retained.

## Build inside the temporary Fedora AArch64 QEMU VM

Transfer this checkout into the VM, then run there:

```sh
sudo dnf install kiwi qemu-img git distribution-gpg-keys
sudo ./build-image.sh Workstation-KDE-Test
```

The wrapper installs the pinned signing key and refuses an existing output
directory. Use a fresh second argument for each subsequent attempt.
Expected output: Gravity-Linux.aarch64-0.0.0.raw below the output directory.
Never pass host block devices as build targets.

Validate the XML/profile selection without building:

```sh
kiwi-ng --profile=Workstation-KDE-Test image info --description . --print-xml
```

Resolve packages before a build (after installing the key as the wrapper does):

```sh
sudo kiwi-ng --profile=Workstation-KDE-Test image info --description . --resolve-package-list
```

Successful XML validation is not a completed dependency transaction or image
build. Kernel, Mesa, U-Boot, and the bootloader must be Gravity builds; config.sh
fails if a stock package was substituted or the M4 DTB is missing. The image
configuration assembles stage 2 via update-m1n1 on the ESP. Stage 1 remains a
separate installer-bundle asset. No builder login credentials are added to images.

## Remaining release work

- Complete COPR builds, resolve dependencies, build the raw image, and test it.
- Package the raw image using the separate installer-data tooling, with Gravity
  artwork, macOS 26.6.2, immutable artifact URLs/checksums, and j773gap-only
  support. This repository does not upload images or installer metadata.
- Validate speaker support and stop using the temporary test profile for release.
- Publish the signed COPR repository before building the final release profile.

Only the two KDE profiles above are supported. Obsolete exporters, cloud-user
templates, alternate variants and upstream publishing/CI configuration have
been removed; they remain recoverable from Git history.

## Checks before publishing

`edit_boot_install.sh` runs after KIWI's final bootloader installation, mounts
the supplied ext4 boot partition, and recreates `/grub2/grubenv` with the real
`grub2-editenv`. It preserves existing settings but removes the stale Btrfs
`env_block` pointer. It checks the filesystem type and replacement contents;
SELinux attributes are preserved. Do not move this into `config.sh` or
`pre_disk_sync.sh`, where `/boot` is still on the build filesystem.

The installer-data packaging tools also check the environment inside `boot.img`
and reject a raw-block pointer. They require this sibling checkout and `debugfs`
from e2fsprogs. The check alone can be run without mounting or modifying the image:

```sh
python3 root/usr/share/gravity-image-test/grub-environment.py --check-image /path/to/boot.img
```

Run `bash check.sh` for local recipe, permission and branding checks. Validate
both profiles with KIWI in Fedora as described above. These checks do not
replace dependency resolution, image creation or hardware testing.

The checked-in key is the public COPR signing key, not a private key. Keep
images, RPMs, test credentials and TLS private keys outside this repository.

Remaining upstream names are intentional: `alsa-ucm-asahi` is an installed
Fedora dependency, and legacy audio/platform package names occur in exclusion
guards. `m1n1`, `apple_m1`, Apple device-tree names and the Fedora EFI path are
compatibility identifiers, not Gravity branding. Do not mechanically rename
them without changing their providers. Attribution in NOTICE is preserved.

## License

GPL-3.0-or-later; see COPYING. Upstream attribution and history are preserved.
