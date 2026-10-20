"""Actualiza únicamente el acceso propio del conciliador de Uruguay."""
from pathlib import Path
import json,os,plistlib,shlex,subprocess,shutil,tempfile,time

NAME='Conciliador IATA Uruguay'
IDS={'uy.sevens.conciliador.iata','uy.sevens.conciliador.iata.abrir'}

def write_changed(path,data):
    if path.exists() and path.read_bytes()==data:return False
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(data)
    return True

def refresh(target,desktop=None):
    target=Path(target)
    settings=json.loads((target/'settings.json').read_text(encoding='utf-8'))
    if settings['kind']!='IATA':return
    version=settings['version']
    marker=target/'logs/desktop_identity.txt'
    if desktop is None and marker.exists() and marker.read_text().strip()==version:return
    if os.name=='nt':
        # WScript resuelve el Escritorio real, incluido OneDrive.
        script='''param($Root,$Name,$Version,$DesktopOverride)
$ErrorActionPreference='Stop'
$shell=New-Object -ComObject WScript.Shell
$desktop=if($DesktopOverride){$DesktopOverride}else{$shell.SpecialFolders.Item('Desktop')}
$destination=Join-Path $desktop ($Name+'.lnk')
$old=Join-Path $desktop 'Conciliador IATA Maveric.lnk'
$target=Join-Path $Root 'Abrir Conciliador IATA Maveric.bat'
if((Test-Path $old) -and -not(Test-Path $destination)) {
    $link=$shell.CreateShortcut($old)
    if($link.TargetPath -eq $target){Move-Item -LiteralPath $old -Destination $destination}
}
$link=$shell.CreateShortcut($destination)
if($link.TargetPath -and $link.TargetPath -ne $target){throw 'El acceso Uruguay existente apunta a otro programa'}
$link.TargetPath=$target;$link.WorkingDirectory=$Root
$link.IconLocation=(Join-Path $Root 'assets/uruguay-v3.7.7.ico')+',0'
$link.Description='Conciliador IATA Uruguay '+$Version
$link.Save()
'''
        file=target/'logs/actualizar_acceso_uruguay.ps1'
        write_changed(file,script.encode('utf-8-sig'))
        subprocess.run(['powershell','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(file),str(target),NAME,version,str(desktop or '')],check=True,timeout=30)
    else:
        desktop=Path(desktop) if desktop else Path.home()/'Desktop'
        old=desktop/'Conciliador IATA Maveric.app'
        bundle=desktop/(NAME+'.app')
        existing=bundle if bundle.exists() else old if old.exists() else None
        if existing:
            info=plistlib.loads((existing/'Contents/Info.plist').read_bytes())
            if info.get('CFBundleIdentifier') not in IDS:raise ValueError('El acceso existente pertenece a otro programa')
        # Construir y firmar un bundle limpio; el original se conserva hasta verificarlo.
        logs=target/'logs';logs.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='desktop-',dir=logs) as temp:
            candidate=Path(temp)/(NAME+'.app')
            contents=candidate/'Contents';resources=contents/'Resources';macos=contents/'MacOS'
            icon='Uruguay-'+version
            write_changed(resources/(icon+'.icns'),(target/'assets/Conciliador_IATA_Maveric.icns').read_bytes())
            write_changed(macos/'UruguayLauncher',(target/'assets/mac_launcher').read_bytes())
            (macos/'UruguayLauncher').chmod(0o755)
            command='#!/bin/bash\nexec /bin/zsh '+shlex.quote(str(target/'launchers/Abrir_Conciliador_Sevens_Mac.command'))+' >> '+shlex.quote(str(logs/'acceso_escritorio.log'))+' 2>&1\n'
            write_changed(resources/'launch.sh',command.encode())
            info=dict(CFBundleExecutable='UruguayLauncher',CFBundleName=NAME,CFBundleDisplayName=NAME,CFBundleIdentifier='uy.sevens.conciliador.iata.abrir',CFBundleIconFile=icon,CFBundlePackageType='APPL',CFBundleVersion=version,NSHighResolutionCapable=True,LSUIElement=True)
            write_changed(contents/'Info.plist',plistlib.dumps(info))
            for command in (['codesign','--force','--deep','--sign','-',str(candidate)],['codesign','--verify','--deep','--strict',str(candidate)]):
                result=subprocess.run(command,check=True,timeout=30,capture_output=True,text=True)
            backup=None
            if existing:
                backup=target/'backups'/('desktop_'+version+'_'+str(time.time_ns()))/existing.name
                backup.parent.mkdir(parents=True,exist_ok=True)
                shutil.move(str(existing),str(backup))
            try:
                shutil.move(str(candidate),str(bundle))
            except BaseException:
                if backup and not existing.exists():shutil.move(str(backup),str(existing))
                raise
            os.utime(bundle,None)
    write_changed(marker,(version+'\n').encode())
