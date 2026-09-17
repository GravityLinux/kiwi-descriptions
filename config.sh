#!/bin/bash

set -euxo pipefail

#======================================
# Functions...
#--------------------------------------
test -f /.kconfig && . /.kconfig
test -f /.profile && . /.profile

#======================================
# Greeting...
#--------------------------------------
echo "Configure image: [$kiwi_iname]-[$kiwi_profiles]..."

#======================================
# Set SELinux booleans
#--------------------------------------
## Fixes KDE Plasma, see rhbz#2058657
setsebool -P selinuxuser_execmod 1

#======================================
# Clear machine specific configuration
#--------------------------------------
## Clear machine-id on pre generated images
rm -f /etc/machine-id
echo 'uninitialized' > /etc/machine-id
## remove random seed, the newly installed instance should make its own
rm -f /var/lib/systemd/random-seed

#======================================
# Configure grub correctly
#--------------------------------------
## Disable submenus to match Fedora
echo "GRUB_DISABLE_SUBMENU=true" >> /etc/default/grub
## Disable recovery entries to match Fedora
echo "GRUB_DISABLE_RECOVERY=true" >> /etc/default/grub
## Disable OS prober. OS selection on apple silicon systems has to go through
## the native startup disk selection
echo "GRUB_DISABLE_OS_PROBER=true" >> /etc/default/grub

if [[ "$kiwi_profiles" == *"-Desktop"* ]]; then
	## Enable menu_auto_hide to match Fedora anaconda installs
	## Set boot_success to avoid displaying the grub menu on first boot
	grub2-editenv /boot/grub2/grubenv set menu_auto_hide=1 boot_indeterminate=1
fi

#======================================
# Delete & lock the root user password
#--------------------------------------
passwd -d root
passwd -l root

#======================================
# Setup default services
#--------------------------------------

## Enable persistent journal
mkdir -p /var/log/journal

#======================================
# Setup firstboot initial setup
#--------------------------------------

if [[ "$kiwi_profiles" != *"GNOME"* ]] && [[ "$kiwi_profiles" != *"KDE"* ]]; then
	## Enable initial-setup
	systemctl enable initial-setup.service
	## Enable reconfig mode
	touch /etc/reconfigSys
fi

## Enable swap setup on firstboot
systemctl enable gravity-setup-swap-firstboot.service

## Enable extras install on firstboot; this will only run if the extras are
## actually present (and self disable afterwards)
systemctl enable gravity-extras-firstboot.service

#======================================
# Setup default target
#--------------------------------------
if [[ "$kiwi_profiles" == *"GNOME"* ]] || [[ "$kiwi_profiles" == *"KDE"* ]]; then
	systemctl set-default graphical.target
else
	systemctl set-default multi-user.target
fi

#======================================
# Import GPG keys
#--------------------------------------

releasever=$(rpm --eval '%{fedora}')
rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$releasever-primary
rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-gravity
echo "Packages within this disk image"
rpm -qa --qf '%{size}\t%{name}-%{version}-%{release}.%{arch}\n' |sort -rn

# Note that running rpm recreates the rpm db files which aren't needed or wanted
rm -f /var/lib/rpm/__db*

#======================================
# Override `DEFAULTKERNEL` in /etc/sysconfig/kernel
# The file is now owned by grubby
#======================================
sed -i 's:\(DEFAULTKERNEL=\)kernel-core:\1kernel-16k-core:' /etc/sysconfig/kernel

#======================================
# Generate boot.bin
#======================================
# Fail closed if a stock package silently satisfied a Gravity dependency.
for package in kernel-16k-core mesa-dri-drivers mesa-vulkan-drivers gravity-bootloader uboot-images-armv8; do
    [[ "$(rpm -q --qf '%{RELEASE}' "$package")" == *gravity* ]]
done
test -s /boot/dtb/apple/t8132-j773g.dtb

if [[ "$kiwi_profiles" == *"Workstation-KDE-Test"* ]]; then
    # Do not expose internal speakers without the downstream safety stack.
    install -Dm644 /usr/share/gravity-image-test/no-internal-audio.conf /etc/modprobe.d/gravity-test-no-internal-audio.conf
    install -Dm644 /usr/share/gravity-image-test/dracut-no-internal-audio.conf /etc/dracut.conf.d/gravity-test-no-internal-audio.conf
    systemctl mask speakersafetyd.service
    for forbidden in gravity-platform-metapackage gravity-platform-metapackage-audio asahi-audio speakersafetyd; do
        if rpm -q "$forbidden"; then
            echo "Unexpected audio dependency in test image: $forbidden" >&2
            exit 1
        fi
    done
    touch /etc/gravity-hardware-test-image
    # Keep this explicitly non-release image on the same staging repository.
    sed -i 's|/fedora-\$releasever-\$basearch/|/fedora-$releasever-$basearch-devel/|' /etc/yum.repos.d/gravity.repo
    # Rebuild after installing the initramfs driver exclusion. The builder is
    # not the target Mac: host-only detection would reject gravity-firmware.
    dracut --force --regenerate-all --no-hostonly
fi
update-m1n1 /boot/efi/m1n1/boot.bin
test -s /boot/efi/m1n1/boot.bin
rm /boot/efi/.builder

exit 0
