@echo off
chcp 65001 > nul
echo Ejecutando tarea...

.\venv\Scripts\python.exe run.py --channel "@jops2015"
timeout /t 2
.\venv\Scripts\python.exe run.py --channel "@jobmag"
timeout /t 2
.\venv\Scripts\python.exe run.py --channel "@saudia_jobs"
timeout /t 2

powershell -c "(New-Object Media.SoundPlayer 'C:\Windows\Media\tada.wav').PlaySync()"
powershell -c "(New-Object Media.SoundPlayer 'C:\Windows\Media\tada.wav').PlaySync()"
powershell -c "(New-Object Media.SoundPlayer 'C:\Windows\Media\tada.wav').PlaySync()"
echo ¡Listo!