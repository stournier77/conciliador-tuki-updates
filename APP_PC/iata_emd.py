"""Corrección acotada: importes positivos EMD truncados por la búsqueda desplazada."""
import re


def apply_emd_amount_fix(namespace):
    original_audit = namespace['audit_net']
    original_exact = namespace['find_exact']
    section = namespace['section_after_usd2']
    to_cents = namespace['to_cents']
    if getattr(original_audit, '_emd_fixed', False):
        return

    def corrected(det, previous):
        text = str(det or '')
        if 'USD2' not in text or not re.search(r'(?:EMDS|EMDA)\d{10}', text):
            return None
        # Sólo corregir la lectura positiva desplazada; conservar negativos y demás reglas.
        if not previous[2].startswith('posicional_campo_'):
            return None
        field = section(text)[60:72]
        if not re.fullmatch(r'\d{12}', field) or int(field) == 0:
            return None
        cents = int(field)
        if to_cents(previous[0]) == cents:
            return None
        return cents / 100, field, 'emd_positivo_campo_completo_60_71'

    def audit_net(det):
        previous = original_audit(det)
        return corrected(det, previous) or previous

    def find_exact(det, amount):
        fixed = corrected(det, original_audit(det))
        if fixed is None:
            return original_exact(det, amount)
        if to_cents(amount) == to_cents(fixed[0]):
            return fixed
        return None, fixed[1], 'emd_importe_no_coincide_campo_completo'

    audit_net._emd_fixed = True
    namespace['audit_net'] = audit_net
    namespace['find_exact'] = find_exact
