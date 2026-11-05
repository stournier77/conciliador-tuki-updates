import importlib.util
import io
from pathlib import Path
import unittest
from datetime import datetime
from unittest.mock import Mock
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject

ROOT=Path(__file__).resolve().parents[1]


def load(folder='APP_MAC'):
    spec=importlib.util.spec_from_file_location('control_'+folder,ROOT/folder/'iata_pdf_control.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def fake_pdf(pages,total='-459.77',currency='USD'):
    writer=PdfWriter()
    for i,texts in enumerate(pages):
        page=writer.add_blank_page(width=841,height=595)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        if i==0:texts=[(10,580,'FCAGBILLDET BSP URUGUAY'),(10,560,'Billing Period: 261004 (22-OCT-2026 to 31-OCT-2026)'),(10,540,'GRAND TOTAL ('+currency+')'),(800,540,total)]+texts
        commands=[]
        for x,y,text in texts:
            text=text.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
            commands.append(f'BT /F1 5.35 Tf 1 0 0 1 {x} {y} Tm ({text}) Tj ET')
        stream=DecodedStreamObject();stream.set_data('\n'.join(commands).encode('ascii'))
        page[NameObject('/Contents')]=writer._add_object(stream)
    result=io.BytesIO();writer.write(result);return result.getvalue()


def header(y=350,doc='0000000001',kind='ACMA'):
    return [(23,y,'045'),(42,y,kind),(66,y,doc),(114,y,'26OCT26'),(222,y,'CA')]


def record(source='PDF',amount=-45977,doc='0000000001',company='045',kind='ACMA',when='2026-10-26'):
    data={'Tipo':kind,'Compañía':company,'Documento':doc,'Fecha':when,'Moneda':'USD',source+' centavos':amount}
    data.update({'Página':2} if source=='PDF' else {'Línea TXT':10})
    return data


class PdfControlTests(unittest.TestCase):
    def test_real_pdf_coordinates_last_column_and_currency(self):
        for folder in ('APP_MAC','APP_PC'):
            mod=load(folder)
            pdf=fake_pdf([header()+[(270,350,'-1277.70'),(800,350,'-459.77')]])
            data=mod.parse_detail_pdf(pdf)
            self.assertEqual(data['records'][0]['PDF centavos'],-45977)
            self.assertEqual(data['grand_cents'],-45977);self.assertEqual(data['issues'],[])
            self.assertEqual(data['period'],'261004')
            with self.assertRaisesRegex(ValueError,'Uruguay en USD'):
                mod.parse_detail_pdf(fake_pdf([header()+[(800,350,'-459.77')]],currency='EUR'))

    def test_split_payment_and_page_continuation(self):
        mod=load()
        same_page=header(kind='TKTT')+[(270,350,'264.73'),(222,338,'CC'),(270,338,'483.33'),(222,326,'**'),(800,326,'231.13')]
        data=mod.parse_detail_pdf(fake_pdf([same_page],total='231.13'))
        self.assertEqual(data['records'][0]['PDF centavos'],23113);self.assertEqual(data['issues'],[])
        page1=header(y=76,kind='TKTT')+[(270,76,'264.73'),(222,64,'CC')]
        page2=[(222,480,'**'),(800,480,'231.13')]
        data=mod.parse_detail_pdf(fake_pdf([page1,page2],total='231.13'))
        self.assertEqual(data['records'][0]['PDF centavos'],23113)
        self.assertEqual(data['records'][0]['Página neto'],2);self.assertEqual(data['issues'],[])

    def test_unreadable_rows_and_incomplete_pdf_never_pass(self):
        mod=load()
        pdf=fake_pdf([header()+[(800,350,'-459.77')]+header(y=300,doc='0000000002')],total='-500.00')
        result=mod.parse_detail_pdf(pdf)
        self.assertTrue(any('No se pudo leer' in i['Observación'] for i in result['issues']))
        self.assertTrue(any('incompleto' in i['Observación'] for i in result['issues']))
        with self.assertRaisesRegex(ValueError,'documentos legibles'):
            mod.parse_detail_pdf(fake_pdf([[]]))

    def test_matches_missing_differences_grouping_and_unknown_amount(self):
        mod=load()
        self.assertEqual(mod.compare_records([record()],[record('TXT')])[0]['Estado'],'Coincide')
        data=mod.compare_records([record()],[record('TXT',-127770)])[0]
        self.assertEqual(data['Estado'],'Diferencia');self.assertEqual(data['Diferencia TXT-PDF'],-817.93)
        self.assertEqual(data['Neto PDF'],-459.77);self.assertEqual(data['Neto TXT'],-1277.70)
        self.assertEqual(mod.compare_records([record()],[])[0]['Estado'],'Sólo en PDF')
        self.assertEqual(mod.compare_records([],[record('TXT')])[0]['Estado'],'Sólo en TXT')
        self.assertEqual(mod.compare_records([record()],[record('TXT',None)])[0]['Estado'],'TXT no interpretable')
        grouped=mod.compare_records([record(amount=-20000),record(amount=-25977)],[record('TXT')])[0]
        self.assertEqual(grouped['Diferencia TXT-PDF'],0);self.assertEqual(grouped['Estado'],'Cantidad de registros distinta')
        for changed in (record('TXT',company='134'),record('TXT',kind='RFND'),record('TXT',when='2026-10-27')):
            self.assertEqual(len(mod.compare_records([record()],[changed])),2)

    def test_txt_uses_existing_parsers_without_mutating_namespace(self):
        mod=load()
        ns={'parse_iata_date':lambda *args:datetime(2026,10,26),'parse_acma_importe':Mock(return_value=(-459.77,'field')),'parse_adma_importe':Mock(return_value=(100.0,'field')),'parse_rfnd_cash_cc':Mock(return_value=(None,-500,'000000000000','cc','method',0,'')),'audit_net':Mock(return_value=(100,'field','method'))}
        original=ns.copy()
        raw=b'DET045 ACMA0000000001 USD2000\nDET045 RFND0000000002 USD2000\nDET045 TKTT0000000003 USD2000'
        rows=mod.parse_txt_records(raw,ns)
        self.assertEqual([r['TXT centavos'] for r in rows],[-45977,0,10000])
        self.assertEqual(ns,original)
        ns['parse_acma_importe'].side_effect=ValueError('Campo ilegible')
        bad=mod.parse_txt_records(b'DET045 ACMA0000000001 USD2000',ns)[0]
        self.assertIsNone(bad['TXT centavos']);self.assertEqual(bad['Fecha'],'2026-10-26')

    def test_comparison_workbook_and_no_document_overlap(self):
        import pandas as pd
        mod=load();ns={'parse_iata_date':lambda *args:datetime(2026,10,26),'parse_acma_importe':lambda *args:(-459.77,'field')}
        parsed={'records':[record()],'issues':[],'grand_cents':-45977,'period':'261004'}
        result=mod.make_control(b'',b'DET045 ACMA0000000001 USD2000',ns,parsed)
        self.assertEqual(result['details'].iloc[0]['Estado'],'Coincide')
        excel=pd.ExcelFile(io.BytesIO(mod.control_excel(result)))
        self.assertIn('Diferencias',excel.sheet_names);self.assertIn('Totales por tipo',excel.sheet_names)
        self.assertEqual(len(pd.read_excel(excel,sheet_name='Diferencias')),0)
        with self.assertRaisesRegex(ValueError,'misma semana'):
            mod.make_control(b'',b'DET045 ACMA0000000099 USD2000',ns,parsed)

if __name__=='__main__':unittest.main()
