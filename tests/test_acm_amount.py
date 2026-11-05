import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


def sample(kind='ACMA',total=-45977,auxiliary=-127770,tail=-45977,doc='0000000000'):
    fields=list('0'*154)
    def amount(cents):return ('-'+f'{abs(cents):011d}') if cents<0 else f'{cents:012d}'
    fields[0:12]=amount(-33200)
    fields[60:72]=amount(total)
    fields[83:95]=amount(auxiliary)
    tail_field='-'+f'{abs(tail):010d}' if tail<0 else f'{tail:011d}'
    return 'DET000 CREDIT MEMOS '+kind+doc+'USD2'+''.join(fields)+'     I '+tail_field+'0'*12


class AcmAmountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('acm_engine',ROOT/'APP_MAC/sevens_engine.py')
        cls.engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.engine)

    def namespace(self):
        ns={'__file__':str(ROOT/'APP_MAC/app.py')};exec(self.engine.legacy_code(),ns)
        return ns

    def patch(self,namespace,folder):
        spec=importlib.util.spec_from_file_location('acm_'+folder,ROOT/folder/'iata_acm.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.apply_acm_amount_fix(namespace)
        return module

    def test_total_field_instead_of_largest_or_last_amount(self):
        for folder in ('APP_MAC','APP_PC'):
            ns=self.namespace()
            self.assertEqual(ns['parse_acma_importe'](sample())[0],-1277.70)
            originals={k:v for k,v in ns.items() if callable(v)}
            mod=self.patch(ns,folder)
            for k,v in originals.items():
                if k!='parse_acma_importe':self.assertIs(ns[k],v)
            # Varios números e importes: la regla no depende de un documento concreto.
            for doc in ('0000000001','1234567890','9999999999'):
                self.assertEqual(ns['parse_acma_importe'](sample(doc=doc))[0],-459.77)
            for cents in (0,-1,-4995,-21700,-39904,-429900,-3103200,-123456789):
                self.assertEqual(ns['parse_acma_importe'](sample(total=cents))[0],cents/100)
            # Un tail distinto no debe reemplazar el total: caso histórico 399.04.
            self.assertEqual(ns['parse_acma_importe'](sample(total=-39904,auxiliary=-3490,tail=-34900))[0],-399.04)
            previous=ns['parse_acma_importe'];mod.apply_acm_amount_fix(ns)
            self.assertIs(previous,ns['parse_acma_importe'])

    def test_other_types_and_manual_exceptions_unchanged(self):
        for folder in ('APP_MAC','APP_PC'):
            ns=self.namespace();original=ns['parse_acma_importe']
            lines=[sample(kind=k) for k in ('SPCR','TKTT','EMDS','EMDA','RFND','ADMA','SPDR','CANX','CANN')]
            before=[original(line) for line in lines]
            overrides={doc:original(sample(doc=doc),doc) for doc in ns['ACMA_OVERRIDES']}
            self.patch(ns,folder)
            self.assertEqual(before,[ns['parse_acma_importe'](line) for line in lines])
            for doc,value in overrides.items():self.assertEqual(value,ns['parse_acma_importe'](sample(doc=doc),doc))

    def test_invalid_acm_does_not_guess_another_amount(self):
        ns=self.namespace();self.patch(ns,'APP_MAC')
        for line in (sample().replace('USD2','EUR2'),sample().split('USD2')[0]+'USD2'+'0'*65):
            with self.assertRaisesRegex(ValueError,'campo total del ACM'):
                ns['parse_acma_importe'](line)

if __name__=='__main__':unittest.main()
