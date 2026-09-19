"""Fast structural checks; KIWI in Fedora is the schema/solver authority."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class RecipeTests(unittest.TestCase):
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
