@echo off
echo Iniciando Checker de Clientes...
echo.

REM Verifica se o Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python não encontrado. Instale em https://python.org
    pause
    exit /b
)

REM Instala dependências se necessário
echo Verificando dependências...
pip install -r requirements.txt --quiet

echo.
echo Abrindo o app no navegador...
python -m streamlit run app.py
pause
