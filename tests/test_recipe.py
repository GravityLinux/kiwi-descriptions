"""Fast structural checks; KIWI in Fedora is the schema/solver authority."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class RecipeTests(unittest.TestCase):
    def test_m4_boot_arguments(self):
        tree = ET.parse(ROOT / 'platforms/workstation.xml').getroot()
        image_type = tree.find("preferences[@profiles='WorkstationCommon']/type")
        args = image_type.attrib['kernelcmdline'].split()
        for arg in ('rhgb', 'quiet', 'nohlt', 'idle=nop', 'arm64.nowfxt',
                    'appledrm.hdmi_audio=1'):
            self.assertEqual(args.count(arg), 1, arg)
        for name in ('Workstation-KDE', 'Workstation-KDE-Test', 'Workstation-Sway-Experimental'):
            profile = tree.find(f"profiles/profile[@name='{name}']")
            self.assertIsNotNone(profile.find("requires[@profile='WorkstationCommon']"))

    def test_sway_experimental_is_separate_from_stable_kde(self):
        trees = [ET.parse(path).getroot() for folder in ('components', 'platforms', 'repositories')
                 for path in (ROOT / folder).glob('*.xml')]
        profiles = {p.attrib['name']: p for tree in trees for p in tree.findall('profiles/profile')}
        def closure(name):
            result = {name}
            for requirement in profiles[name].findall('requires'):
                result |= closure(requirement.attrib['profile'])
            return result
        sway = closure('Workstation-Sway-Experimental')
        kde = closure('Workstation-KDE')
        self.assertTrue({'Stable', 'Experimental', 'Sway-Desktop'} <= sway)
        self.assertNotIn('KDE-Desktop', sway)
        self.assertNotIn('Experimental', kde)
        def packages(selected):
            return {p.attrib['name'] for tree in trees for group in tree.findall('packages')
                    if group.attrib.get('profiles') in selected for p in group.findall('package')}
        self.assertTrue({'sway', 'sway-config-fedora', 'sddm-wayland-sway',
                         'initial-setup-gui-wayland-sway', 'gravity-repos-experimental'} <= packages(sway))
        self.assertNotIn('gravity-platform-metapackage-plasma', packages(sway))
        self.assertIn('gravity-platform-metapackage-plasma', packages(kde))
        repos = {repo.attrib['alias']: repo for tree in trees for repo in tree.findall('repository')}
        self.assertEqual(repos['gravity'].attrib['priority'], repos['gravity-experimental'].attrib['priority'])

    def test_no_obsolete_publishers_or_repository_endpoints(self):
        for name in ('builder.py', 'make-asahi-installer-package.sh', 'repositories/asahi.xml', '.zuul.yaml'):
            self.assertFalse((ROOT / name).exists(), name)
        for directory in ('repositories', 'components', 'platforms'):
            for path in (ROOT / directory).glob('*.xml'):
                contents = path.read_text()
                self.assertNotIn('results/@asahi/', contents)
                self.assertNotIn('fedora-asahi-remix.org', contents)
                self.assertNotIn('Fedora-Asahi-Remix', contents)
        config = ET.parse(ROOT / 'config.xml').getroot()
        self.assertEqual(config.attrib['name'], 'Gravity-Linux')
        self.assertEqual(config.attrib['displayname'], 'Gravity Linux')
        for path in ROOT.rglob('*'):
            if path.is_file() and '.git' not in path.parts and path.suffix in ('.pem', '.key'):
                self.fail(f'Unexpected key material: {path}')

    def test_active_includes_and_repositories(self):
        def load(path):
            tree = ET.parse(path).getroot()
            yield tree
            for include in tree.findall('include'):
                yield from load(ROOT / include.attrib['from'].removeprefix('this://./'))
        trees = list(load(ROOT / 'config.xml'))
        self.assertEqual(trees[0].findtext('preferences/release-version'), '44')
        self.assertEqual(trees[0].findtext('preferences/rpm-check-signatures'), 'true')
        for tree in trees:
            for repo in tree.findall('repository'):
                url = repo.find('source').attrib['path']
                self.assertNotIn('@asahi', url)
                self.assertNotIn('$', url)
                self.assertIsNotNone(repo.find('source/signing'))

    def test_audio_profiles_use_kernel_protection(self):
        tree = ET.parse(ROOT / 'platforms/workstation.xml').getroot()
        def names(profile, kind):
            return {e.attrib['name'] for p in tree.findall('packages')
                    if p.attrib.get('profiles') == profile for e in p.findall(kind)}
        common = names('WorkstationCommon', 'package')
        self.assertNotIn('gravity-platform-metapackage', common)
        self.assertIn('gravity-platform-metapackage-core', common)
        for package in ('pipewire', 'pipewire-alsa', 'pipewire-pulseaudio', 'wireplumber'):
            self.assertIn(package, common)
        for package in ('speakersafetyd', 'gravity-speakersafetyd', 'asahi-audio'):
            self.assertIn(package, names('WorkstationCommon', 'ignore'))
        config = (ROOT / 'config.sh').read_text()
        self.assertNotIn('systemctl mask speakersafetyd.service', config)
        self.assertIn('CONFIG_SND_SOC_APPLE_T8132_SPEAKER=y', config)
        self.assertIn('CONFIG_SND_SOC_TAS2764=y', config)
        self.assertIn('CONFIG_SND_SOC_APPLE_MCA=y', config)
        self.assertIn('rm -f /etc/modprobe.d/gravity-test-no-internal-audio.conf', config)
        self.assertFalse((ROOT / 'root/usr/share/gravity-image-test/no-internal-audio.conf').exists())
        self.assertIn('dracut --force --regenerate-all --no-hostonly', config)
        self.assertIn('t8132-j773g.dtb', config)


if __name__ == '__main__':
    unittest.main()
