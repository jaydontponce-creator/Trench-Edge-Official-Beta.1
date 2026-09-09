import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve()/"backend"))
from app.weekly import run_weekly_refresh
print(run_weekly_refresh())
