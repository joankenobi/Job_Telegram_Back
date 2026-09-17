@echo off
chcp 65001 > nul
echo Ejecutando tarea...

.\venv\Scripts\python.exe run.py --channel "@rrhh_Venezuela"
timeout /t 2
.\venv\Scripts\python.exe run.py --channel "@TRABAJOYPUBLICIDAD2018"
timeout /t 2
.\venv\Scripts\python.exe run.py --channel "@jobsencaracas"
.\venv\Scripts\python.exe run.py --channel "@trabajos_remotos_latam"
.\venv\Scripts\python.exe run.py --channel "@vacantesremotas"
.\venv\Scripts\python.exe run.py --channel "@STEMJobsLATAM"
timeout /t 2
.\venv\Scripts\python.exe run.py --channel "@rrhh_Venezuela" --extract_info_from_text
.\venv\Scripts\python.exe run.py --channel "@TRABAJOYPUBLICIDAD2018" --extract_info_from_text
.\venv\Scripts\python.exe run.py --channel "@jobsencaracas" --extract_info_from_text
.\venv\Scripts\python.exe run.py --channel "@trabajos_remotos_latam" --extract_info_from_text
.\venv\Scripts\python.exe run.py --channel "@vacantesremotas" --extract_info_from_text
.\venv\Scripts\python.exe run.py --channel "@STEMJobsLATAM" --extract_info_from_text

powershell -c "(New-Object Media.SoundPlayer 'C:\Windows\Media\tada.wav').PlaySync()"
powershell -c "(New-Object Media.SoundPlayer 'C:\Windows\Media\tada.wav').PlaySync()"
powershell -c "(New-Object Media.SoundPlayer 'C:\Windows\Media\tada.wav').PlaySync()"
echo ¡Listo!
pause
