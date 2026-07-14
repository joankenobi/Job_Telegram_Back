import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
os.chdir(SCRIPT_DIR)
sys.path.insert(0, str(SCRIPT_DIR))

from telegram_capture.cli import main

if __name__ == "__main__":
    main()