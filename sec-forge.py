"""SecForge 的直接运行入口。"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_MODULES = Path(__file__).with_name("sec-forge")
sys.path.insert(0, str(PROJECT_MODULES))

from main import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
