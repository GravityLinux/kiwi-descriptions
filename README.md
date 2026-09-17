# Gravity Linux KIWI descriptions

Fedora 44 / AArch64 / KDE recipe for the T8132 M4 Mac mini (j773g).
Based on Fedora Asahi's f44 branch at
`960ea8dc8fb33952a874bb4da94a07a055bb11ab`; original history is preserved.

## Profiles

- `Workstation-KDE-Test`: temporary hardware bring-up image. Omits the umbrella
  and audio metapackages, installs their non-audio integration subpackages, and
  blocks snd_soc_macaudio and snd_soc_apple_mca in modprobe and initramfs.
  Speakersafetyd is masked. Internal audio is deliberately unavailable.
- `Workstation-KDE`: eventual release profile, retaining the full Gravity platform
  metapackage and its downstream speakersafetyd requirement. Not release-ready.

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
