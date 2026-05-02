@echo off
:: 1. Entra na pasta do projeto
cd /d "C:\Users\Lucas\automacao_gupy_rj"

:: 2. Registra o horário da tentativa no log
echo. >> erro_log.txt
echo ======================================== >> erro_log.txt
echo Data/Hora: %date% %time% >> erro_log.txt
echo ======================================== >> erro_log.txt

:: 3. Força o Python a aceitar emojis (UTF-8) no terminal do Windows
set PYTHONIOENCODING=utf-8

:: 4. Tenta rodar o script e joga os erros (2) e mensagens (1) para o log
call venv\Scripts\activate.bat
python main.py >> erro_log.txt 2>&1

echo Fim da execucao em: %time% >> erro_log.txt