from pathlib import Path
import sys


API_ROOT = Path(__file__).resolve().parent / "apps" / "api"

if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))
