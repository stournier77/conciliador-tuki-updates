from pathlib import Path
import json,os,plistlib,sys,tempfile,unittest
from unittest.mock import patch
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launchers'))
import desktop_identity as identity

class DesktopIdentityTests(unittest.TestCase):
    def make_target(self,root):
        target=root/'installation';(target/'assets').mkdir(parents=True)
        (target/'settings.json').write_text(json.dumps({'kind':'IATA','version':'3.7.6'}))
        (target/'assets/Conciliador_IATA_Maveric.icns').write_bytes(b'icon')
        (target/'assets/mac_launcher').write_bytes(b'native')
        desktop=root/'Desktop';desktop.mkdir()
        return target,desktop

    @unittest.skipIf(os.name=='nt','Bundle Mac')
    def test_upgrade_existing_mac_bundle_and_preserve_launcher_history(self):
        with tempfile.TemporaryDirectory() as temp:
            target,desktop=self.make_target(Path(temp))
            old=desktop/'Conciliador IATA Maveric.app'
            (old/'Contents/Resources').mkdir(parents=True)
            (old/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'uy.sevens.conciliador.iata.abrir'}))
            (old/'Contents/Resources/keep.txt').write_text('keep')
            with patch.object(identity.subprocess,'run') as sign:
                identity.refresh(target,desktop)
                self.assertEqual(sign.call_count,5)
            app=desktop/'Conciliador IATA Uruguay.app'
            self.assertFalse(old.exists())
            info=plistlib.loads((app/'Contents/Info.plist').read_bytes())
            self.assertEqual(info['CFBundleDisplayName'],'Conciliador IATA Uruguay')
            self.assertEqual(info['CFBundleVersion'],'3.7.6')
            self.assertEqual(info['CFBundleIconFile'],'Uruguay-3.7.6')
            self.assertEqual(next((target/'backups').glob('desktop_*/*.app/Contents/Resources/keep.txt')).read_text(),'keep')
            self.assertIn(str(target/'launchers/Abrir_Conciliador_Sevens_Mac.command'),(app/'Contents/Resources/launch.sh').read_text())

    @unittest.skipIf(os.name=='nt','Bundle Mac')
    def test_unrelated_bundle_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as temp:
            target,desktop=self.make_target(Path(temp))
            bundle=desktop/'Conciliador IATA Uruguay.app';(bundle/'Contents').mkdir(parents=True)
            data=plistlib.dumps({'CFBundleIdentifier':'another.app'})
            (bundle/'Contents/Info.plist').write_bytes(data)
            with self.assertRaises(ValueError):identity.refresh(target,desktop)
            self.assertEqual((bundle/'Contents/Info.plist').read_bytes(),data)

    @unittest.skipIf(os.name=='nt','Bundle Mac')
    def test_signing_failure_keeps_previous_shortcut_untouched(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            target,desktop=self.make_target(Path(temp))
            old=desktop/'Conciliador IATA Maveric.app';(old/'Contents').mkdir(parents=True)
            data=plistlib.dumps({'CFBundleIdentifier':'uy.sevens.conciliador.iata.abrir'})
            (old/'Contents/Info.plist').write_bytes(data)
            with patch.object(identity.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'codesign')):
                with self.assertRaises(subprocess.CalledProcessError):identity.refresh(target,desktop)
            self.assertEqual((old/'Contents/Info.plist').read_bytes(),data)
            self.assertFalse((desktop/'Conciliador IATA Uruguay.app').exists())

    @unittest.skipIf(os.name=='nt','Bundle Mac')
    def test_refresh_keeps_bundle_directory_and_stages_outside_synced_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            target,desktop=self.make_target(Path(temp))
            bundle=desktop/'Conciliador IATA Uruguay.app';(bundle/'Contents').mkdir(parents=True)
            (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'uy.sevens.conciliador.iata.abrir'}))
            inode=bundle.stat().st_ino
            with patch.object(identity.subprocess,'run') as signing,patch.object(identity.shutil,'move',side_effect=AssertionError('No mover el bundle')):
                identity.refresh(target,desktop)
            self.assertEqual(bundle.stat().st_ino,inode)
            candidate=Path(signing.call_args_list[0].args[0][-1])
            self.assertNotIn(str(target),str(candidate))
            self.assertEqual((bundle/'Contents/MacOS/UruguayLauncher').read_bytes(),b'native')

    def test_windows_script_uses_actual_desktop_and_correct_target(self):
        with tempfile.TemporaryDirectory() as temp:
            target,desktop=self.make_target(Path(temp))
            with patch.object(identity,'os',SimpleNamespace(name='nt')),patch.object(identity.subprocess,'run') as run:
                identity.refresh(target,desktop)
            args=run.call_args.args[0]
            self.assertIn(str(target),args)
            script=(target/'logs/actualizar_acceso_uruguay.ps1').read_text(encoding='utf-8-sig')
            self.assertIn("SpecialFolders.Item('Desktop')",script)
            self.assertIn('Abrir Conciliador IATA Maveric.bat',script)
            self.assertIn('$link.TargetPath -eq $target',script)
            self.assertIn("$link.IconLocation",script)

if __name__=='__main__':unittest.main()
