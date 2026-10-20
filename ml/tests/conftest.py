import sys
from pathlib import Path

# Pipeline scripts live in ml/src and import each other as top-level modules.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
