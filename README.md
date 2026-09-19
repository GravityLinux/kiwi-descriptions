# Gravity Linux KIWI descriptions

Fedora 44 / AArch64 / KDE recipe for the T8132 M4 Mac mini (j773g).
Based on Fedora Asahi's f44 branch at
`960ea8dc8fb33952a874bb4da94a07a055bb11ab`; original history is preserved.

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
checking, and the checked-in Gravity COPR signing key. No Asahi COPRs are used
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
- Adapt the inherited installer ZIP/metadata exporter for Gravity artwork,
  macOS 26.6.2, immutable artifact URLs/checksums, and j773gap-only support.
  **Do not use builder.py or make-asahi-installer-package.sh yet**: they retain
  upstream naming, firmware metadata, and publishing behavior.
- Validate speaker support and stop using the temporary test profile for release.
- Publish the signed COPR repository before building the final release profile.

Inactive upstream GNOME/Server/Minimal fragments and CI scripts are retained
for reference, but are not supported by the Gravity build wrapper.

## License

GPL-3.0-or-later; see COPYING. Upstream attribution and history are preserved.
