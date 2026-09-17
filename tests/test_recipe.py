"""Fast structural checks; KIWI in Fedora is the schema/solver authority."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class RecipeTests(unittest.TestCase):
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

    def test_audio_profiles_are_separate(self):
        tree = ET.parse(ROOT / 'platforms/workstation.xml').getroot()
        def names(profile, kind):
            return {e.attrib['name'] for p in tree.findall('packages')
                    if p.attrib.get('profiles') == profile for e in p.findall(kind)}
        release = names('Workstation-KDE', 'package')
        test = names('Workstation-KDE-Test', 'package')
        self.assertIn('gravity-platform-metapackage', release)
        self.assertNotIn('gravity-platform-metapackage', test)
        self.assertIn('gravity-platform-metapackage-core', test)
        self.assertIn('speakersafetyd', names('Workstation-KDE-Test', 'ignore'))
        config = (ROOT / 'config.sh').read_text()
        self.assertIn('systemctl mask speakersafetyd.service', config)
        self.assertIn('dracut --force --regenerate-all --no-hostonly', config)
        self.assertIn('t8132-j773g.dtb', config)


if __name__ == '__main__':
    unittest.main()
