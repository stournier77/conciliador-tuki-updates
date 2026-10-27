import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


def sample(kind='EMDS',cents=2238474,field=None):
    financial=list('0'*154)
    financial[60:72]=field if field is not None else f'{cents:012d}'
    return 'DET000 '+kind+'0000000000USD2'+''.join(financial)+'     I '+(' '*30)


class EmdAmountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('engine_for_emd',ROOT/'APP_MAC/sevens_engine.py')
        cls.engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.engine)

    def namespace(self,folder):
        ns={'__file__':str(ROOT/folder/'app.py')}
        exec(self.engine.legacy_code(),ns)
        return ns

    def patch(self,ns,folder):
        spec=importlib.util.spec_from_file_location('emd_'+folder,ROOT/folder/'iata_emd.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        mod.apply_emd_amount_fix(ns)
        return mod

    def test_complete_amount_and_no_false_match(self):
        for folder in ('APP_MAC','APP_PC'):
            ns=self.namespace(folder)
            self.assertEqual(ns['audit_net'](sample())[0],2384.74)
            originals={k:v for k,v in ns.items() if callable(v)}
            mod=self.patch(ns,folder)
            for k,v in originals.items():
                if k not in ('audit_net','find_exact'):self.assertIs(ns[k],v)
            for kind in ('EMDS','EMDA'):
                for cents in (1000000,2238474,9999999,123456789):
                    det=sample(kind,cents)
                    self.assertEqual(ns['audit_net'](det)[0],cents/100)
                    self.assertEqual(ns['find_exact'](det,cents/100)[0],cents/100)
                self.assertIsNone(ns['find_exact'](sample(kind),2384.74)[0])
            previous=ns['audit_net'];mod.apply_emd_amount_fix(ns)
            self.assertIs(ns['audit_net'],previous)

    def test_unaffected_types_small_zero_negative_and_malformed(self):
        for folder in ('APP_MAC','APP_PC'):
            ns=self.namespace(folder)
            lines=[sample(kind) for kind in ('TKTT','ADMA','SPDR','RFND','ACMA','SPCR','CANX','CANN')]
            lines += [sample(kind,cents) for kind in ('EMDS','EMDA') for cents in (0,1,1940,238474,999999)]
            lines += [sample(field='-00000000106'),sample(field='000002X38474'),'',sample().replace('USD2','EUR2')]
            amounts=(0,1,19.4,2384.74,22384.74,-1.06)
            before=[(ns['audit_net'](line),tuple(ns['find_exact'](line,a) for a in amounts)) for line in lines]
            self.patch(ns,folder)
            after=[(ns['audit_net'](line),tuple(ns['find_exact'](line,a) for a in amounts)) for line in lines]
            self.assertEqual(before,after)

if __name__=='__main__':unittest.main()
