# Checker de Clientes

Ferramenta web para consolidar bases de leads, validar telefones e CPFs, remover duplicatas e exportar clientes prontos para disparo no WhatsApp.

## O que faz

- Une múltiplas planilhas em uma só base consolidada
- Valida telefones brasileiros (DDD, formato, números falsos/sequenciais)
- Valida CPF e CNPJ pelo dígito verificador
- Remove duplicatas por telefone e por CPF
- Complementa dados incompletos cruzando planilhas principal + incompleta
- Separa clientes válidos de pendentes (com motivo do problema)
- Exporta tudo em `.xlsx` pronto para usar

## Telas

**Checker de Leads** — processa as planilhas, exibe métricas e permite filtrar por DDD, fornecedor ou clientes sem nome antes de exportar.

**Unificar Planilhas** — une vários arquivos em um só, útil para consolidar resultados do CheckNumber antes de reimportar.

## Instalação

Requer Python 3.10 ou superior.

```bash
pip install -r requirements.txt
```

## Como rodar

**Windows** — dê dois cliques em `rodar.bat`.

**Terminal**:
```bash
python -m streamlit run app.py
```

O app abre automaticamente no navegador em `http://localhost:8501`.

## Formatos suportados

`.xlsx` · `.xls` · `.csv` · `.txt`

As colunas são detectadas automaticamente — não é necessário padronizar o nome das colunas antes de importar. O app reconhece variações como `telefone`, `celular`, `fone`, `whatsapp`; `cpf`, `documento`, `cnpj`; `nome`, `cliente`, `razao social`; entre outros.

## Testando

A pasta `testes/` contém duas planilhas prontas para experimentar todas as funcionalidades:

| Arquivo | Usar como |
|---|---|
| `testes/planilha_principal.xlsx` | Planilha Principal |
| `testes/planilha_incompleta.xlsx` | Planilha Incompleta |

Cenários cobertos: clientes válidos, duplicatas, telefone falso, dados incompletos, complemento de informações entre planilhas.

## Estrutura do projeto

```
checker_clientes_python/
├── app.py                  # interface Streamlit
├── client_merger.py        # lógica de merge e processamento
├── phone_utils.py          # validação de telefones
├── cpf_utils.py            # validação de CPF e CNPJ
├── static/style.css        # estilos da interface
├── .streamlit/config.toml  # tema do Streamlit
├── testes/                 # planilhas de exemplo
└── requirements.txt
```
