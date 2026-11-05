"""Lectura posicional del total ACM; no elegir importes por su tamaño."""
import re


def apply_acm_amount_fix(namespace):
    original = namespace['parse_acma_importe']
    section = namespace['section_after_usd2']
    overrides = namespace['ACMA_OVERRIDES']
    if getattr(original, '_acm_fixed', False):
        return

    def parse_acma_importe(det, doc=None):
        text = str(det or '')
        match = re.search(r'ACMA(\d{10})', text)
        # SPCR y las excepciones manuales conservan exactamente su tratamiento.
        if match is None or doc in overrides:
            return original(det, doc)
        field = section(text)[60:72] if 'USD2' in text else ''
        # Campo completo: signo y once dígitos, o doce dígitos sin signo.
        if not re.fullmatch(r'-\d{11}|\d{12}', field):
            raise ValueError('No se reconoce el campo total del ACM ' + match[1] + '. Revisá el TXT IATA.')
        return int(field) / 100, field + '_acma_total_posicional_60_71'

    parse_acma_importe._acm_fixed = True
    namespace['parse_acma_importe'] = parse_acma_importe
