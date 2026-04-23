"""
Lógica de merge e processamento de clientes.
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from phone_utils import normalize_phone, extract_ddd, validate_phone, looks_like_phone, is_valid_phone
from cpf_utils import normalize_cpf, is_valid_cpf_or_cnpj



@dataclass
class Client:
    nome: str = ''
    nome_original: Optional[str] = None
    telefone: str = ''
    telefone_normalizado: str = ''
    telefones_alternativos: list = field(default_factory=list)
    cpf: str = ''
    email: str = ''
    endereco: str = ''
    ddd: str = '00'
    origem: str = ''
    origens: dict = field(default_factory=dict)
    fornecedor: str = ''
    pending_reasons: dict = field(default_factory=dict)


@dataclass
class ProcessingStats:
    total_planilhas_incompletas: int = 0
    registros_incompletos: int = 0
    registros_principais: int = 0
    clientes_encontrados: int = 0
    clientes_novos: int = 0
    dados_complementados: int = 0
    duplicidades_removidas: int = 0
    duplicidades_por_cpf: int = 0
    total_final: int = 0
    total_pendentes: int = 0
    fornecedores: list = field(default_factory=list)



def _sanitize_name(name: str) -> Optional[str]:
    if not name:
        return None
    cleaned = re.sub(r'[,;?!@#$%^&*()\=+\[\]{}|\\<>~`\'":.\/\-_]', ' ', name)
    cleaned = re.sub(r'\d', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    if not cleaned or len(cleaned) < 2:
        return None
    if re.search(r'[^a-zA-ZÀ-ÿ\s]', cleaned):
        return None
    return cleaned


def _has_repeated_characters(name: str) -> bool:
    if not name:
        return False
    lower = name.lower()
    for i in range(len(lower) - 2):
        c = lower[i]
        if c == ' ':
            continue
        if lower[i + 1] == c and lower[i + 2] == c:
            return True
    return False


def _is_valid_name(name: Optional[str]) -> bool:
    if not name or len(name) < 2:
        return False
    if re.search(r'[^a-zA-ZÀ-ÿ\s]', name):
        return False
    return True


def _is_numeric_only(value: str) -> bool:
    normalized = re.sub(r'[\s\-().\\/]', '', value)
    return bool(re.match(r'^\d{8,}$', normalized))


def _find_column_value(row: dict, possible_names: list, is_name_field: bool = False) -> str:
    lower_keys = {k.lower(): k for k in row.keys()}

    # correspondência exata
    for name in possible_names:
        lower_name = name.lower()
        if lower_name in lower_keys:
            orig_key = lower_keys[lower_name]
            value = str(row[orig_key] or '').strip()
            if is_name_field and _is_numeric_only(value):
                continue
            return value

    # correspondência parcial (apenas para campos não-nome)
    if not is_name_field:
        for name in possible_names:
            lower_name = name.lower()
            for lk, ok in lower_keys.items():
                if lower_name in lk:
                    return str(row[ok] or '').strip()

    return ''


def _classify_numeric_value(value: str, strict_ddd: bool = False,
                             strict_cellphone: bool = False) -> str:
    if not value:
        return 'unknown'
    normalized = re.sub(r'\D', '', value)

    if len(normalized) == 14:
        return 'cpf'

    if len(normalized) == 11:
        if is_valid_cpf_or_cnpj(normalized):
            return 'cpf'
        if looks_like_phone(normalized, strict_ddd, strict_cellphone):
            return 'phone'
        return 'cpf'

    if len(normalized) == 10:
        if looks_like_phone(normalized, strict_ddd, strict_cellphone):
            return 'phone'

    return 'unknown'


def _extract_client_data(row: dict, strict_ddd: bool = False,
                          strict_cellphone: bool = False) -> dict:
    telefone = _find_column_value(row, ['telefone','phone','tel','celular','fone','whatsapp','whats'])
    cpf      = _find_column_value(row, ['cpf','cpf/cnpj','cnpj','documento','doc'])
    nome     = _find_column_value(row, ['nome','name','cliente','razao','razao_social',
                                         'razão social','razao social'], True)
    email    = _find_column_value(row, ['email','e-mail','mail'])
    endereco = _find_column_value(row, ['endereco','endereço','address','logradouro','rua'])
    fornecedor = _find_column_value(row, ['fornecedor','supplier','fonte','parceiro','source'])

    nome_original = nome

    if nome and _is_numeric_only(nome):
        tipo = _classify_numeric_value(nome, strict_ddd, strict_cellphone)
        if tipo == 'phone' and not telefone:
            telefone = nome
        elif tipo == 'cpf' and not cpf:
            cpf = nome
        nome = ''

    if telefone:
        tipo = _classify_numeric_value(telefone, strict_ddd, strict_cellphone)
        if tipo == 'cpf' and not cpf:
            cpf = telefone
            telefone = ''

    if cpf:
        tipo = _classify_numeric_value(cpf, strict_ddd, strict_cellphone)
        if tipo == 'phone' and not telefone:
            telefone = cpf
            cpf = ''

    if not telefone or not cpf:
        for key, raw_value in row.items():
            value = str(raw_value or '').strip()
            if not value:
                continue
            tipo = _classify_numeric_value(value, strict_ddd, strict_cellphone)
            if tipo == 'phone' and not telefone:
                telefone = value
            elif tipo == 'cpf' and not cpf:
                cpf = value
            if telefone and cpf:
                break

    telefone_normalizado = normalize_phone(telefone)
    nome_sanitizado = _sanitize_name(nome)

    return {
        'nome': nome_sanitizado or '',
        'nome_original': nome_original,
        'telefone': telefone,
        'telefone_normalizado': telefone_normalizado,
        'cpf': normalize_cpf(cpf),
        'email': email,
        'endereco': endereco,
        'ddd': extract_ddd(telefone_normalizado),
        'fornecedor': fornecedor,
    }


def _merge_clients(existing: Client, new_data: dict, new_origin: str) -> Client:
    origem = existing.origem
    if new_origin and new_origin not in existing.origem:
        origem = f'{existing.origem}, {new_origin}'

    origens = dict(existing.origens)

    nome = existing.nome
    nome_original = existing.nome_original
    if not existing.nome and new_data.get('nome'):
        nome = new_data['nome']
        nome_original = new_data.get('nome_original')
        origens['nome'] = new_origin

    telefone = existing.telefone
    telefone_normalizado = existing.telefone_normalizado
    telefones_alternativos = list(existing.telefones_alternativos)

    new_tel_norm = new_data.get('telefone_normalizado', '')
    if new_tel_norm and new_tel_norm != existing.telefone_normalizado:
        if not existing.telefone:
            telefone = new_data.get('telefone', '')
            telefone_normalizado = new_tel_norm
            origens['telefone'] = new_origin
        else:
            if new_tel_norm not in telefones_alternativos:
                telefones_alternativos.append(new_tel_norm)

    cpf = existing.cpf
    if not existing.cpf and new_data.get('cpf'):
        cpf = new_data['cpf']
        origens['cpf'] = new_origin

    email = existing.email
    if not existing.email and new_data.get('email'):
        email = new_data['email']
        origens['email'] = new_origin

    endereco = existing.endereco
    if not existing.endereco and new_data.get('endereco'):
        endereco = new_data['endereco']
        origens['endereco'] = new_origin

    final_ddd = extract_ddd(telefone_normalizado) if telefone_normalizado else (
        existing.ddd or new_data.get('ddd', '00'))

    return Client(
        nome=nome,
        nome_original=nome_original,
        telefone=telefone,
        telefone_normalizado=telefone_normalizado,
        telefones_alternativos=telefones_alternativos,
        cpf=cpf,
        email=email,
        endereco=endereco,
        ddd=final_ddd,
        origem=origem,
        origens=origens,
        fornecedor=existing.fornecedor or new_data.get('fornecedor', ''),
    )


def _is_fake_phone(telefone_normalizado: str) -> bool:
    if not telefone_normalizado:
        return False
    numero = telefone_normalizado[2:]
    patterns = [
        re.compile(r'^9{8,9}$'),
        re.compile(r'^0{8,9}$'),
        re.compile(r'^1{8,9}$'),
        re.compile(r'^2{8,9}$'),
        re.compile(r'^3{8,9}$'),
        re.compile(r'^4{8,9}$'),
        re.compile(r'^5{8,9}$'),
        re.compile(r'^6{8,9}$'),
        re.compile(r'^7{8,9}$'),
        re.compile(r'^8{8,9}$'),
        re.compile(r'^12345678$'),
        re.compile(r'^123456789$'),
        re.compile(r'^987654321$'),
        re.compile(r'^98765432$'),
    ]
    return any(p.match(numero) for p in patterns)


def _is_ddd_in_valid_range(ddd: str) -> bool:
    if not ddd or ddd == '00':
        return False
    try:
        n = int(ddd)
        return 11 <= n <= 99
    except ValueError:
        return False


def _get_pending_reasons(client: Client) -> dict:
    reasons = {}

    if not client.cpf:
        reasons['cpf_vazio'] = True
    elif not is_valid_cpf_or_cnpj(client.cpf):
        reasons['cpf_invalido'] = True

    if not _is_valid_name(client.nome):
        reasons['nome_invalido'] = True
    elif _has_repeated_characters(client.nome):
        reasons['nome_com_caracteres_repetidos'] = True

    if client.nome_original and _has_repeated_characters(client.nome_original):
        reasons['nome_com_caracteres_repetidos'] = True

    if client.telefone_normalizado:
        if not is_valid_phone(client.telefone_normalizado):
            reasons['telefone_invalido'] = True
        if _is_fake_phone(client.telefone_normalizado):
            reasons['telefone_falso'] = True
        if not _is_ddd_in_valid_range(client.ddd):
            reasons['ddd_invalido'] = True
    else:
        reasons['telefone_vazio'] = True

    return reasons


def _format_pending_reasons(reasons: dict) -> str:
    motivos = []
    if reasons.get('cpf_vazio'):
        motivos.append('CPF/CNPJ não informado')
    elif reasons.get('cpf_invalido'):
        motivos.append('CPF/CNPJ inválido')

    if reasons.get('telefone_vazio'):
        motivos.append('Telefone não informado')
    elif reasons.get('telefone_invalido'):
        if reasons.get('ddd_invalido'):
            motivos.append('Telefone com DDD inválido')
        else:
            motivos.append('Telefone inválido')
    elif reasons.get('telefone_falso'):
        motivos.append('Telefone falso/fictício (ex: 99999-9999)')
    elif reasons.get('ddd_invalido'):
        motivos.append('DDD fora do range válido (11-99)')

    if reasons.get('nome_invalido'):
        motivos.append('Nome inválido ou vazio')
    elif reasons.get('nome_com_caracteres_repetidos'):
        motivos.append('Nome com caracteres repetidos')

    return '; '.join(motivos) if motivos else 'Dados incompletos'



def process_client_files(
    principal_files: list,
    incompleta_files: list,
    strict_ddd: bool = False,
    strict_cellphone: bool = False,
    order_by: str = 'ddd',
) -> dict:
    client_map_by_phone: dict[str, Client] = {}
    client_map_by_cpf: dict[str, Client] = {}
    invalid_phone_clients: list[Client] = []

    registros_incompletos = 0
    registros_principais = 0
    clientes_encontrados = 0
    dados_complementados = 0
    duplicidades_por_cpf = 0

    def get_clean_filename(name: str) -> str:
        return re.sub(r'\.[^/.]+$', '', name)

    def extract_fornecedor(filename: str) -> str:
        clean = get_clean_filename(filename)
        parts = re.split(r'[_\-\s]+', clean)
        parts = [p for p in parts if p]
        return parts[-1].upper() if parts else clean.upper()

    def upsert_client(client: Client, has_valid_phone: bool):
        if has_valid_phone and client.telefone_normalizado:
            client_map_by_phone[client.telefone_normalizado] = client
        for alt in client.telefones_alternativos:
            if alt:
                client_map_by_phone[alt] = client
        if client.cpf and is_valid_cpf_or_cnpj(client.cpf):
            client_map_by_cpf[client.cpf] = client

    def find_existing(tel_norm: str, cpf: str):
        if tel_norm:
            by_phone = client_map_by_phone.get(tel_norm)
            if by_phone:
                return by_phone, 'phone'
        if cpf and is_valid_cpf_or_cnpj(cpf):
            by_cpf = client_map_by_cpf.get(cpf)
            if by_cpf:
                return by_cpf, 'cpf'
        return None, None

    def process_file(file_info: dict, is_principal: bool):
        nonlocal registros_incompletos, registros_principais
        nonlocal clientes_encontrados, dados_complementados, duplicidades_por_cpf

        filename = file_info['name']
        rows = file_info['data']
        file_name_clean = get_clean_filename(filename)
        file_fornecedor = extract_fornecedor(filename)

        for row in rows:
            cd = _extract_client_data(row, strict_ddd, strict_cellphone)

            phone_validation = validate_phone(
                cd.get('telefone', ''), strict_ddd, strict_cellphone)
            has_valid_phone = phone_validation['is_valid']
            has_valid_cpf   = is_valid_cpf_or_cnpj(cd.get('cpf', '')) if cd.get('cpf') else False

            if is_principal:
                registros_principais += 1
            else:
                registros_incompletos += 1

            if not has_valid_phone and not has_valid_cpf:
                pending_reasons = {'dados_incompletos': True}
                if not cd.get('telefone'):
                    pending_reasons['telefone_vazio'] = True
                else:
                    pending_reasons['telefone_invalido'] = True
                    if phone_validation.get('reason') == 'invalid_ddd':
                        pending_reasons['ddd_invalido'] = True
                if not cd.get('cpf'):
                    pending_reasons['cpf_vazio'] = True
                else:
                    pending_reasons['cpf_invalido'] = True
                if not cd.get('nome'):
                    pending_reasons['nome_invalido'] = True

                pc = Client(
                    nome=cd.get('nome', ''),
                    nome_original=cd.get('nome_original'),
                    telefone=cd.get('telefone', ''),
                    telefone_normalizado=cd.get('telefone_normalizado', ''),
                    cpf=cd.get('cpf', ''),
                    email=cd.get('email', ''),
                    endereco=cd.get('endereco', ''),
                    ddd=cd.get('ddd', '00'),
                    origem=file_name_clean,
                    origens={},
                    fornecedor=cd.get('fornecedor') or file_fornecedor,
                    pending_reasons=pending_reasons,
                )
                invalid_phone_clients.append(pc)
                continue

            existing, found_by = find_existing(
                cd.get('telefone_normalizado', ''), cd.get('cpf', ''))

            if existing:
                if found_by == 'cpf':
                    duplicidades_por_cpf += 1
                if not is_principal:
                    clientes_encontrados += 1

                before = {k: bool(getattr(existing, k))
                          for k in ('cpf', 'email', 'endereco', 'nome')}
                merged = _merge_clients(existing, cd, file_name_clean)
                after  = {k: bool(getattr(merged, k))
                          for k in ('cpf', 'email', 'endereco', 'nome')}

                if any(not before[k] and after[k] for k in before):
                    dados_complementados += 1

                upsert_client(merged, has_valid_phone or bool(existing.telefone_normalizado))
            else:
                new_client = Client(
                    nome=cd.get('nome', ''),
                    nome_original=cd.get('nome_original'),
                    telefone=cd.get('telefone', ''),
                    telefone_normalizado=cd.get('telefone_normalizado', ''),
                    cpf=cd.get('cpf', ''),
                    email=cd.get('email', ''),
                    endereco=cd.get('endereco', ''),
                    ddd=cd.get('ddd', '00'),
                    origem=file_name_clean,
                    origens={},
                    fornecedor=cd.get('fornecedor') or file_fornecedor,
                )
                upsert_client(new_client, has_valid_phone)

    # planilhas principais
    for f in principal_files:
        process_file(f, True)

    unique_before = {}
    for c in list(client_map_by_phone.values()) + list(client_map_by_cpf.values()):
        if c.cpf and is_valid_cpf_or_cnpj(c.cpf):
            key = f'cpf:{c.cpf}'
        elif c.telefone_normalizado:
            key = f'tel:{c.telefone_normalizado}'
        else:
            key = f'fallback:{c.origem}:{c.nome_original or c.nome}'
        unique_before[key] = c
    clientes_antes = len(unique_before)

    # planilhas incompletas
    for f in incompleta_files:
        process_file(f, False)

    # deduplicação final
    unique_map = {}

    def get_unique_key(c: Client) -> str:
        if c.cpf and is_valid_cpf_or_cnpj(c.cpf):
            return f'cpf:{c.cpf}'
        if c.telefone_normalizado:
            return f'tel:{c.telefone_normalizado}'
        return f'fallback:{c.origem}:{c.nome_original or c.nome}'

    for c in list(client_map_by_phone.values()) + list(client_map_by_cpf.values()):
        unique_map[get_unique_key(c)] = c

    clientes_novos = max(0, len(unique_map) - clientes_antes)

    # separa válidos de pendentes
    all_clients = list(unique_map.values())
    valid_clients = []
    pending_clients = list(invalid_phone_clients)

    for c in all_clients:
        reasons = _get_pending_reasons(c)
        if reasons:
            c.pending_reasons = reasons
            pending_clients.append(c)
        else:
            valid_clients.append(c)

    def sort_key(c: Client):
        try:
            ddd_n = int(c.ddd)
        except ValueError:
            ddd_n = 0
        if order_by == 'nome':
            return (c.nome.lower(), ddd_n)
        return (ddd_n, c.nome.lower())

    valid_clients.sort(key=sort_key)
    pending_clients.sort(key=sort_key)

    fornecedores = sorted({c.fornecedor for c in valid_clients + pending_clients if c.fornecedor})

    total_registros = registros_principais + registros_incompletos
    total_unicos    = len(all_clients)
    duplicidades_removidas = max(0, total_registros - total_unicos - len(invalid_phone_clients))

    stats = ProcessingStats(
        total_planilhas_incompletas=len(incompleta_files),
        registros_incompletos=registros_incompletos,
        registros_principais=registros_principais,
        clientes_encontrados=clientes_encontrados,
        clientes_novos=clientes_novos,
        dados_complementados=dados_complementados,
        duplicidades_removidas=duplicidades_removidas,
        duplicidades_por_cpf=duplicidades_por_cpf,
        total_final=len(valid_clients),
        total_pendentes=len(pending_clients),
        fornecedores=fornecedores,
    )

    return {
        'clients': valid_clients,
        'pending_clients': pending_clients,
        'stats': stats,
    }


def client_to_export_row(c: Client) -> dict:
    from phone_utils import format_phone
    from cpf_utils import format_cpf
    return {
        'Cliente': c.nome,
        'Telefone': format_phone(c.telefone),
        'Telefones Alternativos': ', '.join(
            format_phone(t) for t in c.telefones_alternativos) if c.telefones_alternativos else '',
        'CPF/CNPJ': format_cpf(c.cpf) if c.cpf else '',
        'Email': c.email or '',
        'Fornecedor': c.fornecedor or '',
        'Origem': c.origem,
        'Origem Nome': c.origens.get('nome', ''),
        'Origem Telefone': c.origens.get('telefone', ''),
        'Origem CPF/CNPJ': c.origens.get('cpf', ''),
    }


def pending_client_to_export_row(c: Client) -> dict:
    from phone_utils import format_phone
    from cpf_utils import format_cpf
    return {
        'Nome Original': c.nome_original or '(vazio)',
        'Nome Limpo': c.nome or '(inválido)',
        'Telefone': format_phone(c.telefone) if c.telefone else '(vazio)',
        'CPF/CNPJ': format_cpf(c.cpf) if c.cpf else '(vazio)',
        'Fornecedor': c.fornecedor or '',
        'Origem': c.origem,
        'Motivo': _format_pending_reasons(c.pending_reasons),
    }
