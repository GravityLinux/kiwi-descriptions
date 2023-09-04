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
# Turn on sticky vendors
#--------------------------------------
echo "allow_vendor_change=False" >> /etc/dnf/dnf.conf

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
## Works around issues with grub-bls
## See: https://github.com/OSInside/kiwi/issues/2198
echo "GRUB_DEFAULT=saved" >> /etc/default/grub
## Disable submenus to match Fedora
echo "GRUB_DISABLE_SUBMENU=true" >> /etc/default/grub
## Disable recovery entries to match Fedora
echo "GRUB_DISABLE_RECOVERY=true" >> /etc/default/grub

#======================================
# Delete & lock the root user password
#--------------------------------------
passwd -d root
passwd -l root

#======================================
# Setup default services
#--------------------------------------

## Enable chrony
systemctl enable sshd.service
## Enable NetworkManager
systemctl enable NetworkManager.service
## Enable chrony
systemctl enable chronyd.service
## Enable persistent journal
mkdir -p /var/log/journal

#======================================
# Setup firstboot initial setup
#--------------------------------------

if [[ "$kiwi_profiles" == *"KDE"* ]]; then
	## Enable calamares
	systemctl enable calamares-firstboot.service
else
	## Enable initial-setup
	systemctl enable initial-setup.service
	## Enable reconfig mode
	touch /etc/reconfigSys
fi

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
echo "Packages within this disk image"
rpm -qa --qf '%{size}\t%{name}-%{version}-%{release}.%{arch}\n' |sort -rn

# Note that running rpm recreates the rpm db files which aren't needed or wanted
rm -f /var/lib/rpm/__db*

#======================================
# Generate boot.bin
#======================================
mkdir -p /boot/efi/m1n1
update-m1n1 /boot/efi/m1n1/boot.bin
rm /boot/.builder

exit 0
