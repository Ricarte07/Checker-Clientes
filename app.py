"""
Checker de Clientes — App Streamlit
"""
import io
import sys
import os
from datetime import date

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

from phone_utils import format_phone
from client_merger import process_client_files, client_to_export_row, pending_client_to_export_row

st.set_page_config(
    page_title='Checker de Clientes',
    page_icon='✅',
    layout='wide',
)


def load_css(path: str):
    with open(path, encoding='utf-8') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


load_css(os.path.join(os.path.dirname(__file__), 'static', 'style.css'))


def read_file(uploaded_file) -> list[dict]:
    name = uploaded_file.name.lower()
    try:
        if name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, dtype=str, keep_default_na=False,
                             encoding='utf-8', on_bad_lines='skip')
            return df.to_dict('records')

        if name.endswith('.txt'):
            text = uploaded_file.read().decode('utf-8', errors='replace')
            lines = [l for l in text.splitlines() if l.strip()]
            if not lines:
                return []
            first = lines[0]
            sep = '\t' if '\t' in first else (';' if ';' in first else ',')
            df = pd.read_csv(io.StringIO('\n'.join(lines)), sep=sep,
                             dtype=str, keep_default_na=False)
            return df.to_dict('records')

        xls = pd.ExcelFile(uploaded_file)
        best_df = pd.DataFrame()
        for sheet in xls.sheet_names:
            df = xls.parse(sheet, dtype=str, keep_default_na=False)
            if len(df) > len(best_df):
                best_df = df
        return best_df.fillna('').to_dict('records')

    except Exception as e:
        st.error(f'Erro ao ler {uploaded_file.name}: {e}')
        return []


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Clientes')
    return buf.getvalue()


def mcard(col, label, value, variant=''):
    col.markdown(
        f'<div class="mcard {variant}"><div class="mlabel">{label}</div>'
        f'<div class="mval">{value:,}</div></div>',
        unsafe_allow_html=True,
    )


def result_header(title, count, dot_color):
    st.markdown(
        f'<div class="result-header">'
        f'<div class="dot {dot_color}"></div>'
        f'<div class="rh-title">{title}</div>'
        f'<div class="rh-count">{count:,} registros</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def page_checker():
    st.markdown("""
    <div class="page-hero">
        <div class="badge">✦ Processamento de Leads</div>
        <h1>Checker de Leads</h1>
        <p>Consolide múltiplas bases, valide telefones e CPFs, remova duplicatas e exporte clientes prontos para disparo.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader('📂 Planilhas Principais')
        st.caption('Bases completas com todos os dados.')
        principal_uploads = st.file_uploader(
            'Arraste ou clique para adicionar',
            type=['xlsx', 'xls', 'csv', 'txt'],
            accept_multiple_files=True,
            key='checker_principais',
        )
    with col2:
        st.subheader('📋 Planilhas Incompletas')
        st.caption('Bases parciais para complementar dados.')
        incompleta_uploads = st.file_uploader(
            'Arraste ou clique para adicionar',
            type=['xlsx', 'xls', 'csv', 'txt'],
            accept_multiple_files=True,
            key='checker_incompletas',
        )

    with st.expander('⚙️ Configurações de validação'):
        c1, c2, c3 = st.columns(3)
        strict_ddd  = c1.checkbox('DDD estrito (lista ANATEL)', value=False)
        strict_cell = c2.checkbox('Celular deve começar com 9', value=False)
        order_by    = c3.radio('Ordenar por', ['ddd', 'nome'], horizontal=True)

    st.divider()

    if st.button('🚀 Processar Planilhas', type='primary',
                 disabled=not principal_uploads and not incompleta_uploads):
        with st.spinner('Processando...'):
            principal_files = [{'name': f.name, 'data': read_file(f)} for f in (principal_uploads or [])]
            incompleta_files = [{'name': f.name, 'data': read_file(f)} for f in (incompleta_uploads or [])]
            result = process_client_files(
                principal_files, incompleta_files,
                strict_ddd=strict_ddd,
                strict_cellphone=strict_cell,
                order_by=order_by,
            )
        st.session_state['checker_result'] = result

    if 'checker_result' not in st.session_state:
        return

    result = st.session_state['checker_result']
    stats = result['stats']
    clients = result['clients']
    pending_clients = result['pending_clients']

    st.markdown('### 📊 Resultado')
    total = stats.registros_principais + stats.registros_incompletos
    m1, m2, m3, m4, m5 = st.columns(5)
    mcard(m1, 'Registros Totais',     total,                          'blue')
    mcard(m2, 'Clientes Válidos',     stats.total_final,              'accent')
    mcard(m3, 'Pendentes',            stats.total_pendentes,          'warn')
    mcard(m4, 'Duplicatas Removidas', stats.duplicidades_removidas,   'danger')
    mcard(m5, 'Complementados',       stats.dados_complementados)

    st.markdown('<div style="margin-top:1.5rem"></div>', unsafe_allow_html=True)
    result_header('Clientes Válidos', len(clients), 'green')

    with st.expander('🔍 Filtrar antes de exportar'):
        fc1, fc2, fc3 = st.columns(3)
        filter_ddd      = fc1.text_input('Filtrar por DDD (ex: 11,21)')
        filter_forn     = fc2.selectbox('Filtrar por Fornecedor', ['Todos'] + stats.fornecedores)
        filter_sem_nome = fc3.checkbox('Somente sem nome')

    filtered = clients
    if filter_ddd.strip():
        ddds = [d.strip() for d in filter_ddd.split(',') if d.strip()]
        filtered = [c for c in filtered if c.ddd in ddds]
    if filter_forn != 'Todos':
        filtered = [c for c in filtered if c.fornecedor == filter_forn]
    if filter_sem_nome:
        filtered = [c for c in filtered if not c.nome]

    if filtered:
        df_valid = pd.DataFrame([client_to_export_row(c) for c in filtered])
        st.dataframe(df_valid, use_container_width=True, height=300)

        st.download_button(
            '⬇️ Baixar Clientes Válidos (.xlsx)',
            data=to_excel_bytes(df_valid),
            file_name=f'clientes_validos_{date.today()}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        tel_df = pd.DataFrame({'Telefone': [format_phone(c.telefone) for c in filtered if c.telefone]})
        st.download_button(
            '📱 Baixar só Telefones (para CheckNumber)',
            data=to_excel_bytes(tel_df),
            file_name=f'telefones_{date.today()}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    else:
        st.info('Nenhum cliente após os filtros.')

    st.markdown('<div style="margin-top:1.5rem"></div>', unsafe_allow_html=True)
    result_header('Pendentes', len(pending_clients), 'yellow')

    if pending_clients:
        df_pend = pd.DataFrame([pending_client_to_export_row(c) for c in pending_clients])
        st.dataframe(df_pend, use_container_width=True, height=250)
        st.download_button(
            '⬇️ Baixar Pendentes (.xlsx)',
            data=to_excel_bytes(df_pend),
            file_name=f'pendentes_{date.today()}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    else:
        st.success('Nenhum cliente pendente!')


def page_unificar():
    st.markdown("""
    <div class="page-hero">
        <div class="badge">✦ Unificação de Bases</div>
        <h1>Unificar Planilhas</h1>
        <p>Una várias planilhas em uma só, mantendo todas as colunas de todos os arquivos. Ideal para consolidar resultados do CheckNumber.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    steps = [
        ('1', 'Exporte Telefones',    'Use o filtro no Checker e exporte sem cabeçalho'),
        ('2', 'Valide no CheckNumber','Verificador de WhatsApp em tempo real'),
        ('3', 'Carregue os Resultados','Adicione as planilhas validadas aqui'),
        ('4', 'Baixe a Unificada',    'Pronta para reimportar no Checker'),
    ]
    for col, (num, title, desc) in zip([c1, c2, c3, c4], steps):
        col.markdown(
            f'<div class="step-card"><div class="step-num">{num}</div>'
            f'<div class="step-title">{title}</div>'
            f'<div class="step-desc">{desc}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="margin-top:1.2rem"></div>', unsafe_allow_html=True)

    uploads = st.file_uploader(
        'Adicione as planilhas para unificar',
        type=['xlsx', 'xls', 'csv', 'txt'],
        accept_multiple_files=True,
        key='unificar_uploads',
    )

    if not uploads:
        return

    all_data = []
    all_columns = set()

    with st.spinner('Lendo planilhas...'):
        for f in uploads:
            rows = read_file(f)
            for r in rows:
                all_columns.update(r.keys())
            all_data.extend(rows)

    cols_list = list(all_columns)
    normalized = [{col: str(row.get(col, '') or '') for col in cols_list} for row in all_data]
    df_merged = pd.DataFrame(normalized, columns=cols_list)

    st.success(f'✅ {len(uploads)} planilha(s) — **{len(all_data):,}** registros | **{len(cols_list)}** colunas')
    st.dataframe(df_merged.head(100), use_container_width=True)
    st.download_button(
        '⬇️ Baixar Planilha Unificada (.xlsx)',
        data=to_excel_bytes(df_merged),
        file_name=f'planilha_unificada_{date.today()}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


PAGES = {
    '✅ Checker de Leads':    page_checker,
    '🗂️ Unificar Planilhas': page_unificar,
}

with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="logo-icon">✅</div>
        <div>
            <div class="logo-text">Checker</div>
            <div class="logo-sub">de Clientes</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="nav-section">Navegação</div>', unsafe_allow_html=True)
    page_name = st.radio('Navegar', list(PAGES.keys()), label_visibility='collapsed')
    st.divider()
    st.markdown('<div style="font-size:12px;color:var(--txt2)">💡 Suporta .xlsx · .xls<br>.csv · .txt</div>',
                unsafe_allow_html=True)

PAGES[page_name]()
