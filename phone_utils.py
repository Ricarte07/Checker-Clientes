"""
Utilitários de validação de telefone.
"""
import re
from typing import Optional

# DDDs válidos no Brasil (ANATEL)
VALID_DDDS = {
    '11','12','13','14','15','16','17','18','19',  # São Paulo
    '21','22','24',                                  # Rio de Janeiro
    '27','28',                                       # Espírito Santo
    '31','32','33','34','35','37','38',              # Minas Gerais
    '41','42','43','44','45','46',                   # Paraná
    '47','48','49',                                  # Santa Catarina
    '51','53','54','55',                             # Rio Grande do Sul
    '61',                                            # Distrito Federal
    '62','64',                                       # Goiás
    '63',                                            # Tocantins
    '65','66',                                       # Mato Grosso
    '67',                                            # Mato Grosso do Sul
    '68',                                            # Acre
    '69',                                            # Rondônia
    '71','73','74','75','77',                        # Bahia
    '79',                                            # Sergipe
    '81','87',                                       # Pernambuco
    '82',                                            # Alagoas
    '83',                                            # Paraíba
    '84',                                            # Rio Grande do Norte
    '85','88',                                       # Ceará
    '86','89',                                       # Piauí
    '91','93','94',                                  # Pará
    '92','97',                                       # Amazonas
    '95',                                            # Roraima
    '96',                                            # Amapá
    '98','99',                                       # Maranhão
}

DDD_TO_STATE = {
    '11':'SP','12':'SP','13':'SP','14':'SP','15':'SP','16':'SP','17':'SP','18':'SP','19':'SP',
    '21':'RJ','22':'RJ','24':'RJ',
    '27':'ES','28':'ES',
    '31':'MG','32':'MG','33':'MG','34':'MG','35':'MG','37':'MG','38':'MG',
    '41':'PR','42':'PR','43':'PR','44':'PR','45':'PR','46':'PR',
    '47':'SC','48':'SC','49':'SC',
    '51':'RS','53':'RS','54':'RS','55':'RS',
    '61':'DF',
    '62':'GO','64':'GO',
    '63':'TO',
    '65':'MT','66':'MT',
    '67':'MS',
    '68':'AC',
    '69':'RO',
    '71':'BA','73':'BA','74':'BA','75':'BA','77':'BA',
    '79':'SE',
    '81':'PE','87':'PE',
    '82':'AL',
    '83':'PB',
    '84':'RN',
    '85':'CE','88':'CE',
    '86':'PI','89':'PI',
    '91':'PA','93':'PA','94':'PA',
    '92':'AM','97':'AM',
    '95':'RR',
    '96':'AP',
    '98':'MA','99':'MA',
}

KNOWN_FAKE_NUMBERS = {
    '99999999','999999999',
    '88888888','888888888',
    '12345678','123456789',
    '00000000','000000000',
    '11111111','111111111',
    '98765432','987654321',
}

FAKE_PHONE_PATTERNS = [
    re.compile(r'^(\d)\1{7,}$'),
    re.compile(r'^12345678\d*$'),
    re.compile(r'^98765432\d*$'),
    re.compile(r'^0{8,}$'),
    re.compile(r'^1{8,}$'),
]


def is_valid_ddd(ddd: str, strict: bool = False) -> bool:
    if strict:
        return ddd in VALID_DDDS
    try:
        n = int(ddd)
        return 11 <= n <= 99
    except ValueError:
        return False


def get_state_from_ddd(ddd: str) -> Optional[str]:
    return DDD_TO_STATE.get(ddd)


def normalize_phone(phone) -> str:
    if not phone:
        return ''
    normalized = re.sub(r'\D', '', str(phone))
    if len(normalized) > 11 and normalized.startswith('55'):
        normalized = normalized[2:]
    if normalized.startswith('0'):
        normalized = normalized[1:]
    return normalized


def extract_ddd(normalized_phone: str) -> str:
    if len(normalized_phone) >= 2:
        return normalized_phone[:2]
    return '00'


def extract_number(normalized_phone: str) -> str:
    if len(normalized_phone) > 2:
        return normalized_phone[2:]
    return normalized_phone


def format_phone(phone) -> str:
    if not phone:
        return ''
    normalized = normalize_phone(phone)
    if len(normalized) == 11:
        return f'({normalized[:2]}) {normalized[2:7]}-{normalized[7:]}'
    elif len(normalized) == 10:
        return f'({normalized[:2]}) {normalized[2:6]}-{normalized[6:]}'
    return str(phone)


def _is_fake_phone_pattern(number_without_ddd: str) -> bool:
    for pattern in FAKE_PHONE_PATTERNS:
        if pattern.match(number_without_ddd):
            return True
    return number_without_ddd in KNOWN_FAKE_NUMBERS


def _has_minimum_entropy(number_without_ddd: str) -> bool:
    digit_counts = {}
    for d in number_without_ddd:
        digit_counts[d] = digit_counts.get(d, 0) + 1
    if len(digit_counts) < 3:
        return False
    max_allowed = len(number_without_ddd) * 0.6
    if any(c > max_allowed for c in digit_counts.values()):
        return False
    return True


def _is_valid_mobile_prefix(number_without_ddd: str) -> bool:
    if len(number_without_ddd) != 9:
        return True
    if number_without_ddd[0] != '9':
        return False
    return number_without_ddd[1] != '0'


def validate_phone(phone, strict_ddd: bool = False, strict_cellphone: bool = False,
                   detect_fake: bool = True) -> dict:
    normalized = normalize_phone(phone)
    ddd = extract_ddd(normalized)
    state = get_state_from_ddd(ddd)

    if not normalized:
        return {'is_valid': False, 'reason': 'empty', 'normalized': '', 'ddd': '00'}

    if len(normalized) < 10 or len(normalized) > 11:
        return {'is_valid': False, 'reason': 'invalid_length', 'normalized': normalized, 'ddd': ddd}

    if not is_valid_ddd(ddd, strict_ddd):
        return {'is_valid': False, 'reason': 'invalid_ddd', 'normalized': normalized, 'ddd': ddd}

    number_without_ddd = extract_number(normalized)
    is_mobile = len(normalized) == 11

    if strict_cellphone and is_mobile and normalized[2] != '9':
        return {'is_valid': False, 'reason': 'invalid_cellphone_format',
                'normalized': normalized, 'ddd': ddd, 'state': state}

    if detect_fake:
        if _is_fake_phone_pattern(number_without_ddd):
            return {'is_valid': False, 'reason': 'fake_number',
                    'normalized': normalized, 'ddd': ddd, 'state': state, 'is_mobile': is_mobile}

        if not _has_minimum_entropy(number_without_ddd):
            return {'is_valid': False, 'reason': 'low_entropy',
                    'normalized': normalized, 'ddd': ddd, 'state': state, 'is_mobile': is_mobile}

        if is_mobile and not _is_valid_mobile_prefix(number_without_ddd):
            return {'is_valid': False, 'reason': 'invalid_prefix',
                    'normalized': normalized, 'ddd': ddd, 'state': state, 'is_mobile': is_mobile}

    return {'is_valid': True, 'normalized': normalized, 'ddd': ddd,
            'state': state, 'is_mobile': is_mobile}


def is_valid_phone(phone, strict_ddd: bool = False, strict_cellphone: bool = False) -> bool:
    return validate_phone(phone, strict_ddd, strict_cellphone)['is_valid']


def looks_like_phone(value: str, strict_ddd: bool = False, strict_cellphone: bool = False) -> bool:
    normalized = re.sub(r'\D', '', value)
    if len(normalized) == 14:
        return False
    if len(normalized) == 11:
        ddd = normalized[:2]
        if not is_valid_ddd(ddd, strict_ddd):
            return False
        if strict_cellphone:
            return normalized[2] == '9'
        return True
    if len(normalized) == 10:
        ddd = normalized[:2]
        return is_valid_ddd(ddd, strict_ddd)
    return False


def is_commercial_number(phone) -> bool:
    normalized = normalize_phone(phone)
    phone_str = str(phone or '')
    if normalized.startswith('0800') or '0800' in phone_str:
        return True
    if normalized.startswith('4000') or normalized.startswith('4004'):
        return True
    if normalized.startswith('3003'):
        return True
    return False
