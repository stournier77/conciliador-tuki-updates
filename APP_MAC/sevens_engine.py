"""Carga verificable del motor ya publicado; no se duplica en este paquete."""
import ast,hashlib,io,zipfile,urllib.request
from pathlib import Path
ARCHIVE_URL='https://raw.githubusercontent.com/stournier77/conciliador-tuki-updates/113753ffa96416c043fb603714fd80aa554a3576/latest_mac.zip'
ARCHIVE_SHA256='014595a544058e06701f2d9504f40ea9a112d4cf9fc747b6274abcdad0c72aef'
SOURCE_SHA256='d18c690c28420cf4763c8c1e396910cf4babeb5fa56f077d3678606b29a81a3d'


def secure_bytes(url):
    """HTTPS verificado: urllib o confianza nativa del sistema como alternativa."""
    import urllib.error,ssl,tempfile,os,subprocess
    from pathlib import Path
    from urllib.parse import urlparse
    if urlparse(url).scheme!='https':raise ValueError('La descarga requiere HTTPS')
    request=urllib.request.Request(url,headers={'User-Agent':'Sevens-Updates','Accept':'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(request,timeout=30) as response:data=response.read(50_000_001)
    except (urllib.error.URLError,ssl.SSLError):
        with tempfile.TemporaryDirectory() as temporary:
            target=Path(temporary)/'download.bin'
            if os.name=='nt':
                env=dict(os.environ,SEVENS_DOWNLOAD_URL=url,SEVENS_DOWNLOAD_TARGET=str(target))
                code="$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri $env:SEVENS_DOWNLOAD_URL -OutFile $env:SEVENS_DOWNLOAD_TARGET -TimeoutSec 90"
                subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',code],env=env,check=True,timeout=100,capture_output=True)
            else:
                subprocess.run(['curl','--fail','--location','--silent','--show-error','--proto','=https','--proto-redir','=https','--connect-timeout','8','--max-time','90',url,'--output',str(target)],check=True,timeout=100,capture_output=True)
            data=target.read_bytes()
    if len(data)>50_000_000:raise ValueError('La descarga excede el tamaño permitido')
    return data

def load_legacy():
    root=Path(__file__).resolve().parent.parent
    cache=root/'runtime_shared'/'iata_engine_3.6.2.py'
    if cache.exists() and hashlib.sha256(cache.read_bytes()).hexdigest()==SOURCE_SHA256:
        return cache.read_text(encoding='utf-8')
    data=secure_bytes(ARCHIVE_URL)
    if hashlib.sha256(data).hexdigest()!=ARCHIVE_SHA256:raise ValueError('No coincide la versión verificada del motor IATA')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        source=z.read('Instalador Conciliador IATA Maveric Mac v3.6.2/Archivos APP/APP_MAC/app.py')
    if hashlib.sha256(source).hexdigest()!=SOURCE_SHA256:raise ValueError('El motor IATA no coincide con el original')
    cache.parent.mkdir(parents=True,exist_ok=True)
    temp=cache.with_suffix('.tmp');temp.write_bytes(source);temp.replace(cache)
    return source.decode('utf-8')

def legacy_code():
    tree=ast.parse(load_legacy())
    nodes=[]
    for node in tree.body:
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr=='set_page_config':break
        # La ubicación de resultados pertenece a la interfaz nueva.
        if isinstance(node,ast.Assign) and any(isinstance(n,ast.Name) and n.id in {'REPORTS_DIR','OUT_DIR'} for n in node.targets):continue
        nodes.append(node)
    return compile(ast.Module(body=nodes,type_ignores=[]),'motor_iata_3.6.2','exec')
