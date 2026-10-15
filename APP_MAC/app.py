from sevens_engine import legacy_code
exec(legacy_code(),globals())
VERSION='3.7.2'
CREATED_LABEL='15/10/2026'
from sevens_paths import output_root
REPORTS_DIR=output_root()
OUT_DIR=REPORTS_DIR

def output_name(start,end):
    s=pd.to_datetime(start);e=pd.to_datetime(end)
    return f"Conciliacion_IATA_{s:%Y-%m-%d}_al_{e:%Y-%m-%d}_{datetime.now():%Y-%m-%d_%H-%M-%S_%f}.xlsx"

from sevens_ui import apply_design, header, sidebar_brand, sidebar_info, file_heading, footer
from sevens_migrate import migrate
st.set_page_config(page_title=APP_NAME,page_icon='🧾',layout='wide',initial_sidebar_state='expanded')
migrate()
apply_design()
device_uuid,device_info=check_device_authorized()
if not device_info:
    st.error('Aplicación no autorizada para este dispositivo.')
    st.warning(f"UUID detectado: {device_uuid or 'No pude detectar UUID'}")
    st.stop()
with st.sidebar:
    sidebar_brand('IATA')
    if st.button('Abrir carpeta de conciliaciones',icon=':material/folder_open:',use_container_width=True,key='abrir_carpeta'):
        REPORTS_DIR.mkdir(parents=True,exist_ok=True)
        if platform.system()=='Darwin': subprocess.Popen(['open',str(REPORTS_DIR)])
        elif os.name=='nt': os.startfile(str(REPORTS_DIR))
        else: subprocess.Popen(['xdg-open',str(REPORTS_DIR)])
    sidebar_info(device_info['name'],VERSION,CREATED_LABEL)
    if st.button('Cerrar aplicación',icon=':material/power_settings_new:',use_container_width=True,key='cerrar_aplicacion'):
        os._exit(0)
header('IATA','Compará la liquidación IATA con los registros de Maveric.')
st.markdown('<h2 class="sevens-section-title">Cargar archivos</h2>',unsafe_allow_html=True)
col1,col2,col3=st.columns(3,gap='medium')
with col1:
    with st.container(border=True,key='upload_iata'):
        file_heading('Subir archivo TXT de IATA')
        txt_file=st.file_uploader('Subir archivo TXT de IATA',type=['txt','TXT'],key='txt_iata',label_visibility='collapsed')
with col2:
    with st.container(border=True,key='upload_maveric'):
        file_heading('Subir Excel de Maveric')
        mav_file=st.file_uploader('Subir Excel de Maveric',type=['xlsx','xls'],key='excel_maveric',label_visibility='collapsed')
with col3:
    with st.container(border=True,key='upload_pdf'):
        file_heading('Subir resumen IATA · opcional')
        resumen_pdf_file=st.file_uploader('Subir resumen IATA · opcional',type=['pdf'],key='pdf_iata',label_visibility='collapsed')
with st.container(border=True):
    periodo=st.date_input('Período IATA',value=(pd.Timestamp.today().date(),pd.Timestamp.today().date()),help='Elegí primero el día inicial y después el día final del período IATA.')

if isinstance(periodo, tuple) and len(periodo) == 2:
    start_date, end_date = periodo
else:
    start_date = end_date = periodo

if st.button("GENERAR CONCILIACIÓN",type="primary",icon=":material/fact_check:",use_container_width=True,key="generar_conciliacion",disabled=not(txt_file and mav_file)):
    if txt_file is None or mav_file is None:
        st.error("Tenés que subir Subir TXT de la IATA y Subir XLS de Maveric original sin títulos.")
    elif pd.Timestamp(start_date) > pd.Timestamp(end_date):
        st.error("La fecha desde no puede ser mayor que la fecha hasta.")
    else:
        try:
            sheets = build_beta2(txt_file, mav_file, start_date, end_date)
            resumen_iata_df, totales_iata_df, total_iata_pdf, diag_pdf_iata = parse_iata_summary_pdf(resumen_pdf_file)
            try:
                pdf_subido = resumen_pdf_file is not None
            except Exception:
                pdf_subido = False
            if pdf_subido:
                if resumen_iata_df is None or resumen_iata_df.empty:
                    resumen_iata_df = pd.DataFrame([{"Categoria":"ERROR","Codigo":"","Sigla":"","Compañia":f"PDF subido, pero sin filas parseadas. Diagnóstico: {diag_pdf_iata}","FOP":"","Cash":0.0,"CC":0.0,"Total":0.0,"RFND Cash":0.0,"RFND CC":0.0,"RFND Total":0.0,"ADMS":0.0,"ACM":0.0,"Tasas y Cargos":0.0,"Monto Cash":0.0,"Taxs sin Comi":0.0,"Neto a pagar":0.0,"Cantidad de docs":0}])
                sheets["Resumen IATA"] = resumen_iata_df
                if total_iata_pdf is not None:
                    sheets["_TOTAL_INFORMADO_IATA_PDF"] = float(total_iata_pdf)
            data = excel_bytes(sheets); filename = output_name(start_date, end_date)
            out_dir = get_period_output_dir(start_date, end_date); (out_dir / filename).write_bytes(data)
            st.success("Conciliación generada correctamente.")
            st.download_button("Descargar Excel conciliado", data=data, file_name=filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            st.info(f"También se guardó una copia en: {out_dir}")
        except Exception as e:
            st.exception(e)

footer()
