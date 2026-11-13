import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evalbench.smoke import run  # noqa: E402


def test_smoke():
    assert run() == 0
