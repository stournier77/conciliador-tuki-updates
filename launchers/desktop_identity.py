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

def current_mac_shortcut(bundle,target):
    """Conservar el bundle de Finder si sus recursos funcionales ya son los correctos."""
    try:
        info=plistlib.loads((bundle/'Contents/Info.plist').read_bytes())
        if info.get('CFBundleIdentifier') not in IDS or info.get('CFBundleExecutable')!='UruguayLauncher':
            return False
        icon=info.get('CFBundleIconFile','')
        if not icon or Path(icon).name!=icon:
            return False
        if not icon.endswith('.icns'):icon+='.icns'
        resources=bundle/'Contents/Resources'
        if (resources/icon).read_bytes()!=(target/'assets/Conciliador_IATA_Maveric.icns').read_bytes():
            return False
        if (bundle/'Contents/MacOS/UruguayLauncher').read_bytes()!=(target/'assets/mac_launcher').read_bytes():
            return False
        command='#!/bin/bash\nexec /bin/zsh '+shlex.quote(str(target/'launchers/Abrir_Conciliador_Sevens_Mac.command'))+' >> '+shlex.quote(str(target/'logs/acceso_escritorio.log'))+' 2>&1\n'
        return (resources/'launch.sh').read_text()==command and os.access(bundle/'Contents/MacOS/UruguayLauncher',os.X_OK)
    except (OSError,ValueError,plistlib.InvalidFileException):
        return False

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
        # Un cambio de versión de la aplicación no requiere recrear su acceso.
        # Conservar también el icono personalizado y los metadatos de Finder/iCloud.
        if existing==bundle and current_mac_shortcut(bundle,target):
            write_changed(marker,(version+'\n').encode())
            return
        # Construir y firmar un bundle limpio; el original se conserva hasta verificarlo.
        logs=target/'logs';logs.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='sevens-desktop-') as temp:
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
                shutil.copytree(existing,backup)
            try:
                if existing and existing!=bundle and not bundle.exists():
                    try:existing.rename(bundle)
                    except OSError:pass
                # Algunos escritorios sincronizados impiden mover el paquete completo.
                # Copiar sobre el acceso conserva su carpeta y evita borrarla primero.
                shutil.copytree(candidate,bundle,dirs_exist_ok=True,copy_function=shutil.copyfile)
                (bundle/'Contents/MacOS/UruguayLauncher').chmod(0o755)
                # Finder puede conservar el metadato visual del acceso anterior.
                subprocess.run(['xattr','-d','com.apple.FinderInfo',str(bundle)],capture_output=True,timeout=10)
                for command in (['codesign','--force','--deep','--sign','-',str(bundle)],['codesign','--verify','--deep','--strict',str(bundle)]):
                    subprocess.run(command,check=True,timeout=30,capture_output=True,text=True)
            except BaseException:
                if backup:
                    shutil.copytree(backup,existing,dirs_exist_ok=True)
                raise
            os.utime(bundle,None)
    write_changed(marker,(version+'\n').encode())
