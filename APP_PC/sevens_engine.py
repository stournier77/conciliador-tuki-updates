"""Carga verificable del motor ya publicado; no se duplica en este paquete."""
import ast,hashlib,io,zipfile,urllib.request
from pathlib import Path
ARCHIVE_URL='https://raw.githubusercontent.com/stournier77/conciliador-tuki-updates/113753ffa96416c043fb603714fd80aa554a3576/latest_mac.zip'
ARCHIVE_SHA256='014595a544058e06701f2d9504f40ea9a112d4cf9fc747b6274abcdad0c72aef'
SOURCE_SHA256='d18c690c28420cf4763c8c1e396910cf4babeb5fa56f077d3678606b29a81a3d'

def load_legacy():
    root=Path(__file__).resolve().parent.parent
    cache=root/'runtime_shared'/'iata_engine_3.6.2.py'
    if cache.exists() and hashlib.sha256(cache.read_bytes()).hexdigest()==SOURCE_SHA256:
        return cache.read_text(encoding='utf-8')
    request=urllib.request.Request(ARCHIVE_URL,headers={'User-Agent':'Sevens-IATA'})
    with urllib.request.urlopen(request,timeout=45) as response:data=response.read()
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
