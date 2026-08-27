@echo off
chcp 65001 > nul

.\venv\Scripts\python.exe run.py --channel "@rrhh_Venezuela"
timeout /t 2
.\venv\Scripts\python.exe run.py --channel "@TRABAJOYPUBLICIDAD2018"
timeout /t 2
.\venv\Scripts\python.exe run.py --channel "@rrhh_Venezuela" --extract-image-text
timeout /t 20
.\venv\Scripts\python.exe run.py --channel "@TRABAJOYPUBLICIDAD2018" --extract-image-text
timeout /t 20
.\venv\Scripts\python.exe run.py --channel "@jobsencaracas" --extract-image-text
timeout /t 20
.\venv\Scripts\python.exe run.py --classify-by-location
