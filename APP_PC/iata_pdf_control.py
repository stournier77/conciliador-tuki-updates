"""Control independiente PDF/TXT. No modifica las funciones de conciliación."""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
import io
import re

TYPES=('TKTT','EMDS','EMDA','ADMA','SPDR','ACMA','SPCR','RFND','CANX','CANN')
DOC_RE=re.compile(r'('+'|'.join(TYPES)+r')(\d{10})')
DATE_RE=re.compile(r'('+'|'.join(TYPES)+r')(\d{10})(?:\d)?(\d{6})')
MONEY_RE=re.compile(r'-?\d[\d,]*\.\d{2}')
MONTHS={m:i for i,m in enumerate(('JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'),1)}
KEY=('Tipo','Compañía','Documento','Fecha')


def cents(value):
    if value is None:return None
    try:
        value=Decimal(str(value).replace(',',''))
        return int((value*100).to_integral_value()) if value.is_finite() else None
    except (InvalidOperation,ValueError,TypeError):return None


def pdf_date(value):
    m=re.fullmatch(r'(\d{2})([A-Z]{3})(\d{2})',value)
    if not m:return ''
    try:return date(2000+int(m[3]),MONTHS[m[2]],int(m[1])).isoformat()
    except (ValueError,KeyError):return ''


def page_rows(words,width,page_number):
    records=[];issues=[]
    anchors=[w for w in words if w['text'] in TYPES and .03*width<w['x0']<.08*width]
    for anchor in anchors:
        row=[w for w in words if abs(w['top']-anchor['top'])<1.3]
        company=next((w['text'] for w in row if w['x0']<anchor['x0'] and re.fullmatch(r'\d{3}',w['text'])),None)
        document=next((w['text'] for w in row if .07*width<w['x0']<.13*width and re.fullmatch(r'\d{10}',w['text'])),None)
        if company is None or document is None:continue
        date_word=next((w['text'] for w in row if .13*width<w['x0']<.2*width and re.fullmatch(r'\d{2}[A-Z]{3}\d{2}',w['text'])),None)
        # CA/CC pueden ocupar dos renglones y el saldo aparecer en un tercero (**).
        # Buscar la primera última-columna dentro del mismo documento, sin tomar subtotales.
        next_top=min((w['top'] for w in anchors if w['top']>anchor['top']+1.3),default=float('inf'))
        candidates=[]
        for word in words:
            if not (word['x0']>.90*width and MONEY_RE.fullmatch(word['text'])):continue
            if not anchor['top']-1.3<=word['top']<min(next_top-1.3,anchor['top']+36):continue
            net_row=[w for w in words if abs(w['top']-word['top'])<1.3]
            continuation=any(.25*width<w['x0']<.30*width and w['text'] in ('CA','CC','AA','**') for w in net_row)
            if abs(word['top']-anchor['top'])<1.3 or continuation:candidates.append(word)
        first_top=min((w['top'] for w in candidates),default=-100)
        amounts=[w for w in candidates if abs(w['top']-first_top)<1.3]
        if len(amounts)!=1 or not pdf_date(date_word or ''):
            issue={'Página':page_number,'Documento':document,'Observación':'No se pudo leer con seguridad la fecha o la última columna.'}
            if not amounts and pdf_date(date_word or '') and anchor is max(anchors,key=lambda w:w['top']):
                issue['_pending']={'Tipo':anchor['text'],'Compañía':company,'Documento':document,'Fecha':pdf_date(date_word),'Moneda':'USD','Página':page_number,'FOP PDF':''}
            issues.append(issue)
            continue
        fop=next((w['text'] for w in row if .25*width<w['x0']<.30*width and re.fullmatch(r'(?:CA|CC|AA|[A-Z]{2})',w['text'])),'')
        records.append({'Tipo':anchor['text'],'Compañía':company,'Documento':document,'Fecha':pdf_date(date_word),'Moneda':'USD','PDF centavos':cents(amounts[0]['text']),'Página':page_number,'FOP PDF':fop})
    return records,issues


def parse_detail_pdf(raw):
    import pdfplumber
    records=[];issues=[];grand=None;period=None;pending=None
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for number,page in enumerate(pdf.pages,1):
            words=page.extract_words();text=' '.join(w['text'] for w in words)
            if number==1:
                if 'FCAGBILLDET' not in text or 'URUGUAY' not in text or set(re.findall(r'GRAND\s+TOTAL\s*\(([A-Z]{3})\)',text))!={'USD'}:
                    raise ValueError('Usá el PDF detallado FCAGBILLDET de IATA Uruguay en USD.')
                match=re.search(r'Billing\s+Period:\s*(\d{6})\s*\(\s*(\d{2}-[A-Z]{3}-\d{4})\s+to\s+(\d{2}-[A-Z]{3}-\d{4})\s*\)',text)
                if match:period=match[1]
                for word in words:
                    if word['text']!='GRAND':continue
                    line=[w for w in words if abs(w['top']-word['top'])<1.3]
                    if not any('USD' in w['text'] for w in line):continue
                    values=[w for w in line if w['x0']>.9*page.width and MONEY_RE.fullmatch(w['text'])]
                    if len(values)==1:grand=cents(values[0]['text'])
            if pending is not None:
                anchors=[w for w in words if w['text'] in TYPES and .03*page.width<w['x0']<.08*page.width]
                first=min((w['top'] for w in anchors),default=page.height*.92)
                candidates=[]
                for w in words:
                    if not (w['x0']>.9*page.width and 95<w['top']<first-1.3 and MONEY_RE.fullmatch(w['text'])):continue
                    if any(.25*page.width<t['x0']<.30*page.width and t['text'] in ('CA','CC','AA','**') and abs(t['top']-w['top'])<1.3 for t in words):candidates.append(w)
                if len(candidates)==1:
                    record=pending.pop('_pending');record['PDF centavos']=cents(candidates[0]['text']);record['Página neto']=number
                    records.append(record)
                else:
                    pending.pop('_pending',None);issues.append(pending)
                pending=None
            rows,warnings=page_rows(words,page.width,number)
            for warning in warnings:
                if '_pending' in warning:pending=warning
                else:issues.append(warning)
            records.extend(rows)
            page.close()
    if pending is not None:
        pending.pop('_pending',None);issues.append(pending)
    if not records:raise ValueError('No se encontraron documentos legibles en el PDF detallado. No se completó el control.')
    total=sum(r['PDF centavos'] for r in records)
    if grand is None:issues.append({'Página':1,'Documento':'','Observación':'No se reconoció el total general del PDF; no se pudo comprobar la cobertura completa.'})
    elif total!=grand:issues.append({'Página':1,'Documento':'','Observación':f'La suma de documentos leídos ({total/100:,.2f}) no coincide con el total general ({grand/100:,.2f}). El control del PDF es incompleto.'})
    return {'records':records,'issues':issues,'grand_cents':grand,'period':period}


def parse_txt_records(raw,namespace):
    text=None
    for encoding in ('utf-8-sig','cp1252','latin-1'):
        try:text=raw.decode(encoding);break
        except UnicodeDecodeError:pass
    records=[]
    for number,line in enumerate(text.splitlines(),1):
        match=DOC_RE.search(line) if line.startswith('DET') else None
        if not match:continue
        kind,doc=match.groups();value=None;method='';note='';when=''
        try:
            parsed=namespace['parse_iata_date'](line,DATE_RE)
            when='' if str(parsed)=='NaT' else parsed.date().isoformat()
        except Exception as exc:note='No se pudo leer la fecha TXT: '+str(exc)
        try:
            if kind in ('ACMA','SPCR'):value,method=namespace['parse_acma_importe'](line,doc)
            elif kind in ('ADMA','SPDR'):value,method=namespace['parse_adma_importe'](line)
            elif kind=='RFND':
                cash,cc,cash_field,*rest=namespace['parse_rfnd_cash_cc'](line)
                # La última columna es el saldo a pagar (cash); CC se informa aparte.
                value=cash
                if cash is None and re.fullmatch(r'0{12}',str(cash_field)):value=0
                method='RFND: saldo efectivo; tarjeta no se suma al saldo IATA'
            elif kind in ('CANX','CANN'):value=0;method='anulación sin importe a pagar'
            else:value,field,method=namespace['audit_net'](line)
        except Exception as exc:
            note=(note+'; ' if note else '')+str(exc)
        record={'Tipo':kind,'Compañía':line[3:6],'Documento':doc,'Fecha':when,'Moneda':'USD','TXT centavos':cents(value),'Línea TXT':number,'Método TXT':method,'Observación TXT':note}
        if 'USD2' not in line:
            record['TXT centavos']=None;record['Observación TXT']='No se reconoce la moneda o el formato USD2.'
        records.append(record)
    if not records:raise ValueError('No se encontraron documentos DET en el TXT IATA.')
    return records


def compare_records(pdf_records,txt_records):
    groups={}
    for source,records in (('PDF',pdf_records),('TXT',txt_records)):
        for r in records:
            key=tuple(r.get(k,'') for k in KEY)
            group=groups.setdefault(key,{'PDF':[],'TXT':[]});group[source].append(r)
    rows=[]
    for key,group in sorted(groups.items()):
        p,t=group['PDF'],group['TXT']
        pvalue=sum(r['PDF centavos'] for r in p) if p else None
        valid=bool(t) and all(r['TXT centavos'] is not None for r in t)
        tvalue=sum(r['TXT centavos'] for r in t) if valid else None
        difference=tvalue-pvalue if tvalue is not None and pvalue is not None else None
        status='Coincide' if difference==0 else 'Diferencia'
        if not p:status='Sólo en TXT'
        elif not t:status='Sólo en PDF'
        elif not valid:status='TXT no interpretable'
        elif difference==0 and len(p)!=len(t):status='Cantidad de registros distinta'
        rows.append(dict(zip(KEY,key),Moneda='USD',Estado=status,**{'Neto TXT':None if tvalue is None else tvalue/100,'Neto PDF':None if pvalue is None else pvalue/100,'Diferencia TXT-PDF':None if difference is None else difference/100,'Páginas PDF':', '.join(map(str,sorted({page for r in p for page in (r['Página'],r.get('Página neto',r['Página']))}))),'Líneas TXT':', '.join(str(r['Línea TXT']) for r in t),'Registros PDF':len(p),'Registros TXT':len(t),'Observación':'Registros repetidos agrupados por tipo, compañía, documento y fecha.' if len(p)>1 or len(t)>1 else '; '.join(r.get('Observación TXT','') for r in t if r.get('Observación TXT'))}))
    return rows


def make_control(raw_pdf,raw_txt,namespace,parsed_pdf=None):
    import pandas as pd
    pdf=parsed_pdf if parsed_pdf is not None else parse_detail_pdf(raw_pdf)
    txt=parse_txt_records(raw_txt,namespace)
    rows=compare_records(pdf['records'],txt)
    if not any(r['Registros PDF'] and r['Registros TXT'] for r in rows):
        raise ValueError('El PDF y el TXT no comparten documentos con la misma compañía, tipo y fecha. Revisá que sean de la misma semana.')
    details=pd.DataFrame(rows)
    def totals(keys):
        output=[]
        for values,frame in details.groupby(keys,dropna=False,sort=True):
            if not isinstance(values,tuple):values=(values,)
            a=frame['Neto TXT'].sum(min_count=1);b=frame['Neto PDF'].sum(min_count=1)
            output.append(dict(zip(keys,values),**{'Moneda':'USD','Neto TXT':round(a,2),'Neto PDF':round(b,2),'Diferencia TXT-PDF':round(a-b,2),'Documentos':len(frame),'Con observaciones':int((frame['Estado']!='Coincide').sum()),'Registros PDF':int(frame['Registros PDF'].sum()),'Registros TXT':int(frame['Registros TXT'].sum())}))
        return pd.DataFrame(output)
    return {'details':details,'totals_type':totals(['Tipo']),'totals_company':totals(['Compañía','Tipo']),'issues':pd.DataFrame(pdf['issues'],columns=['Página','Documento','Observación']),'metadata':{'Moneda':'USD','Período PDF':pdf['period'] or 'No identificado','Total general PDF':None if pdf['grand_cents'] is None else pdf['grand_cents']/100,'Registros PDF':len(pdf['records']),'Registros TXT':len(txt),'Criterio':'Última columna Neto a pagar. Control independiente; no reemplaza los importes de conciliación.'}}


def control_excel(control):
    import pandas as pd
    output=io.BytesIO()
    with pd.ExcelWriter(output,engine='xlsxwriter') as writer:
        pd.DataFrame(list(control['metadata'].items()),columns=['Concepto','Valor']).to_excel(writer,sheet_name='Información',index=False)
        for name,data in (('Diferencias',control['details'].loc[control['details']['Estado']!='Coincide']),('Todos los documentos',control['details']),('Totales por tipo',control['totals_type']),('Totales por compañía',control['totals_company']),('Observaciones PDF',control['issues'])):
            data.to_excel(writer,sheet_name=name,index=False)
        money=writer.book.add_format({'num_format':'#,##0.00;[Red](#,##0.00)'})
        for sheet in writer.sheets.values():sheet.freeze_panes(1,0);sheet.set_column(0,18,19)
        for name,data in (('Diferencias',control['details']),('Todos los documentos',control['details']),('Totales por tipo',control['totals_type']),('Totales por compañía',control['totals_company'])):
            sheet=writer.sheets[name]
            for i,col in enumerate(data.columns):
                if col in ('Neto TXT','Neto PDF','Diferencia TXT-PDF'):sheet.set_column(i,i,20,money)
    return output.getvalue()
