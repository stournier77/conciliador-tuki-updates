# Conciliador IATA — diseño Sevens

Interfaz común aprobada en Tarjetas. Se conservan las funciones de cálculo publicadas. Las salidas van a Documentos/Conciliador IATA/Archivos conciliados, por período (IATA) y por banco y período (Bancos). Los nombres incluyen período, fecha y hora con segundos y fracción para evitar sobrescrituras.

Mismos accesos de escritorio en Mac y Windows, puerto exclusivo, actualización automática desde GitHub Releases con respaldo y recuperación. Cerrar el navegador no obliga a detener la aplicación: el acceso vuelve a abrir la instancia que sigue funcionando. Los instaladores crean el acceso con el logo original. No se eliminan históricos ni configuraciones locales de equipos.

Los paquetes mantienen compatibilidad con los actualizadores anteriores. La primera apertura migra únicamente los archivos del programa al nuevo arranque, sin modificar el acceso de escritorio. El entorno privado Python 3.12 se prepara automáticamente la primera vez. En Windows se usa la resolución de Documentos del sistema.

Pruebas: python -m unittest discover -s tests; en Windows se prueban además la recuperación de Python ausente y la reutilización del entorno con PowerShell. Generar paquetes: python launchers/Preparar_publicacion.py build.

El motor IATA se conserva como dependencia inmutable del paquete público 3.6.2: se obtiene una sola vez de su commit exacto, se verifican SHA256 del paquete y del archivo y se guarda en runtime_shared. Las actualizaciones no eliminan ese caché. La interfaz nueva carga sus definiciones de cálculo sin modificarlas y cambia únicamente presentación, nombres y rutas de salida. No se vuelven a publicar las listas de equipos ni las reglas de conciliación dentro del código nuevo. La primera apertura con el diseño nuevo necesita conexión para obtener esa dependencia.

Corrección HTTPS: si el Python del equipo carece de certificados raíz, la descarga usa curl en Mac o la confianza del sistema en Windows. Se mantiene la validación TLS y SHA256 del paquete. No se modifica la configuración de certificados del equipo.

Resultados en Documentos/App Conciliador IATA Maveric/archivos conciliados. El selector de escritorio abre la carpeta de esta aplicación en Mac y Windows; se mantiene arrastrar archivos. Los históricos de la carpeta anterior se copian sin borrar originales ni sobrescribir.
