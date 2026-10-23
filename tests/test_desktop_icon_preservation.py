import importlib.util
import os
from types import SimpleNamespace
from pathlib import Path
import plistlib
import shlex
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('identity_under_test',ROOT/'launchers/desktop_identity.py')
identity=importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)

class IconPreservationTests(unittest.TestCase):
    def test_existing_native_shortcut_keeps_finder_metadata_on_update(self):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/'install';desktop=Path(temp)/'desktop'
            bundle=desktop/(identity.NAME+'.app')
            resources=bundle/'Contents/Resources';macos=bundle/'Contents/MacOS'
            resources.mkdir(parents=True);macos.mkdir()
            (target/'assets').mkdir(parents=True)
            (target/'settings.json').write_text('{"kind":"IATA","version":"3.7.11"}')
            (target/'assets/mac_launcher').write_bytes(b'native')
            (target/'assets/Conciliador_IATA_Maveric.icns').write_bytes(b'logo')
            (macos/'UruguayLauncher').write_bytes(b'native')
            (macos/'UruguayLauncher').chmod(0o755)
            (resources/'Uruguay-3.7.10.icns').write_bytes(b'logo')
            command='#!/bin/bash\nexec /bin/zsh '+shlex.quote(str(target/'launchers/Abrir_Conciliador_Sevens_Mac.command'))+' >> '+shlex.quote(str(target/'logs/acceso_escritorio.log'))+' 2>&1\n'
            (resources/'launch.sh').write_text(command)
            info=plistlib.dumps(dict(CFBundleIdentifier='uy.sevens.conciliador.iata.abrir',CFBundleExecutable='UruguayLauncher',CFBundleIconFile='Uruguay-3.7.10'))
            (bundle/'Contents/Info.plist').write_bytes(info)
            custom=bundle/'Icon-custom-finder';custom.write_bytes(b'custom icon metadata')
            with patch.object(identity,'os',SimpleNamespace(name='posix',access=os.access,X_OK=os.X_OK)),patch.object(identity.subprocess,'run',side_effect=AssertionError('Must not recreate or sign a healthy shortcut')):
                identity.refresh(target,desktop=desktop)
            self.assertEqual(custom.read_bytes(),b'custom icon metadata')
            self.assertEqual((bundle/'Contents/Info.plist').read_bytes(),info)
            self.assertEqual((target/'logs/desktop_identity.txt').read_text(),'3.7.11\n')
            detached=command.replace('\nexec /bin/zsh ','\n/usr/bin/nohup /bin/zsh ').replace(' 2>&1\n',' 2>&1 < /dev/null &\nexit 0\n')
            (resources/'launch.sh').write_text(detached)
            with patch.object(identity,'os',SimpleNamespace(name='posix',access=os.access,X_OK=os.X_OK)),patch.object(identity.subprocess,'run',side_effect=AssertionError('Must preserve repaired launcher')):
                identity.refresh(target,desktop=desktop)
            self.assertEqual((resources/'launch.sh').read_text(),detached)
            self.assertEqual(custom.read_bytes(),b'custom icon metadata')
            (target/'assets/Conciliador_IATA_Maveric.icns').write_bytes(b'new logo')
            self.assertFalse(identity.current_mac_shortcut(bundle,target))
