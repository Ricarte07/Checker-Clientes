"""
Utilitários de validação de CPF e CNPJ.
"""
import re

SEQUENTIAL_PATTERNS = {
    '12345678909',
    '01234567890',
    '98765432100',
    '10293847560',
}

KNOWN_INVALID_CPFS = {
    '12345678909',
    '11111111111',
    '00000000000',
}


def normalize_cpf(cpf) -> str:
    if not cpf:
        return ''
    return re.sub(r'\D', '', str(cpf))


def format_cpf(cpf) -> str:
    normalized = normalize_cpf(cpf)
    if len(normalized) == 11:
        return f'{normalized[:3]}.{normalized[3:6]}.{normalized[6:9]}-{normalized[9:]}'
    if len(normalized) == 14:
        return f'{normalized[:2]}.{normalized[2:5]}.{normalized[5:8]}/{normalized[8:12]}-{normalized[12:]}'
    return str(cpf)


def format_cpf_masked(cpf) -> str:
    """Formata CPF com dígitos ocultos: 123.456.789-00 → xxx.xxx.789-00"""
    normalized = normalize_cpf(cpf).zfill(11)
    return f'xxx.xxx.{normalized[6:9]}-{normalized[9:11]}'


def _has_all_same_digits(cpf: str) -> bool:
    return bool(re.match(r'^(\d)\1{10}$', cpf))


def _validate_cpf_first_digit(cpf: str) -> bool:
    total = sum(int(cpf[i]) * (10 - i) for i in range(9))
    remainder = (total * 10) % 11
    if remainder in (10, 11):
        remainder = 0
    return remainder == int(cpf[9])


def _validate_cpf_second_digit(cpf: str) -> bool:
    total = sum(int(cpf[i]) * (11 - i) for i in range(10))
    remainder = (total * 10) % 11
    if remainder in (10, 11):
        remainder = 0
    return remainder == int(cpf[10])


def validate_cpf(cpf) -> dict:
    normalized = normalize_cpf(cpf)

    if not normalized:
        return {'is_valid': False, 'reason': 'empty', 'normalized': ''}

    if len(normalized) != 11:
        return {'is_valid': False, 'reason': 'invalid_length', 'normalized': normalized}

    if _has_all_same_digits(normalized):
        return {'is_valid': False, 'reason': 'all_same_digits', 'normalized': normalized}

    if normalized in SEQUENTIAL_PATTERNS or normalized in KNOWN_INVALID_CPFS:
        return {'is_valid': False, 'reason': 'known_invalid', 'normalized': normalized}

    if not _validate_cpf_first_digit(normalized):
        return {'is_valid': False, 'reason': 'invalid_first_digit', 'normalized': normalized}

    if not _validate_cpf_second_digit(normalized):
        return {'is_valid': False, 'reason': 'invalid_second_digit', 'normalized': normalized}

    return {'is_valid': True, 'normalized': normalized}


def is_valid_cpf(cpf) -> bool:
    return validate_cpf(cpf)['is_valid']


def validate_cnpj(cnpj) -> dict:
    normalized = normalize_cpf(cnpj)

    if not normalized:
        return {'is_valid': False, 'reason': 'empty', 'normalized': ''}

    if len(normalized) != 14:
        return {'is_valid': False, 'reason': 'invalid_length', 'normalized': normalized}

    if re.match(r'^(\d)\1{13}$', normalized):
        return {'is_valid': False, 'reason': 'all_same_digits', 'normalized': normalized}

    branch_code = normalized[8:12]
    if branch_code == '0000':
        return {'is_valid': False, 'reason': 'invalid_branch', 'normalized': normalized}

    is_matrix = branch_code == '0001'

    # primeiro dígito verificador
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(normalized[i]) * weights1[i] for i in range(12))
    remainder = total % 11
    digit1 = 0 if remainder < 2 else 11 - remainder
    if digit1 != int(normalized[12]):
        return {'is_valid': False, 'reason': 'invalid_first_digit', 'normalized': normalized}

    # segundo dígito verificador
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(normalized[i]) * weights2[i] for i in range(13))
    remainder = total % 11
    digit2 = 0 if remainder < 2 else 11 - remainder
    if digit2 != int(normalized[13]):
        return {'is_valid': False, 'reason': 'invalid_second_digit', 'normalized': normalized}


    return {'is_valid': True, 'normalized': normalized, 'is_matrix': is_matrix}


def is_valid_cnpj(cnpj) -> bool:
    return validate_cnpj(cnpj)['is_valid']


def is_valid_cpf_or_cnpj(value) -> bool:
    normalized = normalize_cpf(value)
    if len(normalized) == 11:
        return is_valid_cpf(normalized)
    if len(normalized) == 14:
        return is_valid_cnpj(normalized)
    return False


def validate_cpf_or_cnpj(value) -> dict:
    normalized = normalize_cpf(value)
    if len(normalized) == 11:
        return validate_cpf(normalized)
    if len(normalized) == 14:
        return validate_cnpj(normalized)
    return {'is_valid': False, 'reason': 'invalid_length', 'normalized': normalized}
