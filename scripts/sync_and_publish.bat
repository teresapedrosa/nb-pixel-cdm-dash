@echo off
REM ============================================================
REM nb-cdm — sync incremental + geracao do dashboard + publicacao
REM
REM Chamado pelo N8N via Execute Command (Schedule Trigger -> este
REM script). Nao tem logica de negocio aqui - so orquestra os
REM scripts Python que ja fazem o trabalho (data_layer, metrics,
REM render) e publica o resultado no GitHub Pages.
REM
REM Gotchas do Windows evitados de proposito:
REM - "cd /d %~dp0" no topo em vez de "git -C %~dp0" (barra invertida
REM   final de %~dp0 quebra o parsing de aspas em comando git).
REM - Checagem de venv antes de tudo, porque a pasta e sincronizada
REM   por OneDrive e o venv pode sumir sozinho (limpeza/sync).
REM ============================================================

setlocal

cd /d "%~dp0.."

if not exist logs mkdir logs
set LOGFILE=logs\ultimo_sync.log

echo ============================================================ > "%LOGFILE%"
venv\Scripts\python.exe -c "from datetime import datetime; print('Sync iniciado em', datetime.now().strftime('%%d/%%m/%%Y %%H:%%M'))" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo AVISO: venv nao encontrado ou quebrado em venv\Scripts\python.exe >> "%LOGFILE%"
    echo AVISO: venv nao encontrado ou quebrado em venv\Scripts\python.exe
    echo Rode "python -m venv venv" e depois "pip install -r requirements.txt" na pasta do projeto.
    exit /b 1
)

echo [1/4] Sync incremental de issues/activities... >> "%LOGFILE%"
venv\Scripts\python.exe -m src.data_layer >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo ERRO no sync de dados. Ver logs\ultimo_sync.log >> "%LOGFILE%"
    echo ERRO no sync de dados. Ver logs\ultimo_sync.log
    exit /b 1
)

echo [2/4] Calculando metricas... >> "%LOGFILE%"
venv\Scripts\python.exe -m src.metrics >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo ERRO ao calcular metricas. Ver logs\ultimo_sync.log >> "%LOGFILE%"
    echo ERRO ao calcular metricas. Ver logs\ultimo_sync.log
    exit /b 1
)

echo [3/4] Gerando dashboard estatico... >> "%LOGFILE%"
venv\Scripts\python.exe -m src.render >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo ERRO ao gerar o dashboard. Ver logs\ultimo_sync.log >> "%LOGFILE%"
    echo ERRO ao gerar o dashboard. Ver logs\ultimo_sync.log
    exit /b 1
)

echo [4/4] Publicando no GitHub Pages... >> "%LOGFILE%"
git add docs\index.html >> "%LOGFILE%" 2>&1
git commit -m "sync automatico" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo Nada novo para publicar, ou commit falhou - ver logs\ultimo_sync.log >> "%LOGFILE%"
) else (
    git push >> "%LOGFILE%" 2>&1
    if errorlevel 1 (
        echo ERRO no git push. Ver logs\ultimo_sync.log >> "%LOGFILE%"
        echo ERRO no git push. Ver logs\ultimo_sync.log
        exit /b 1
    )
)

echo Concluido. >> "%LOGFILE%"
echo Concluido — ver logs\ultimo_sync.log para detalhes.
endlocal
