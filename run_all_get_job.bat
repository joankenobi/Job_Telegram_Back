@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo deleting old locations file...

rd "C:\Users\Public\Documents\Programacion\telegram back\downloads\locations" /S /Q

echo dowloading the jobs data...
.\venv\Scripts\python.exe run.py --channel "@rrhh_Venezuela"
timeout /t 2
.\venv\Scripts\python.exe run.py --channel "@TRABAJOYPUBLICIDAD2018"
timeout /t 2
.\venv\Scripts\python.exe run.py --channel "@jobsencaracas"
timeout /t 2
.\venv\Scripts\python.exe run.py --channel "@rrhh_Venezuela" --extract-image-text
timeout /t 20
.\venv\Scripts\python.exe run.py --channel "@TRABAJOYPUBLICIDAD2018" --extract-image-text
timeout /t 20
.\venv\Scripts\python.exe run.py --channel "@jobsencaracas" --extract-image-text
timeout /t 20
echo classifying the jobs data and creating the new \locations dir...
.\venv\Scripts\python.exe run.py --channel "@jobsencaracas" --classify-by-location
.\venv\Scripts\python.exe run.py --channel "@TRABAJOYPUBLICIDAD2018" --classify-by-location
.\venv\Scripts\python.exe run.py --channel "@rrhh_Venezuela" --classify-by-location

powershell -c "(New-Object Media.SoundPlayer 'C:\Windows\Media\tada.wav').PlaySync()"

powershell -c "(New-Object Media.SoundPlayer 'C:\Windows\Media\tada.wav').PlaySync()"

powershell -c "(New-Object Media.SoundPlayer 'C:\Windows\Media\tada.wav').PlaySync()"
echo ¡Listo!
pause