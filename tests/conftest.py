"""测试公共初始化。"""

from __future__ import annotations

import sys
from pathlib import Path


项目根目录 = Path(__file__).resolve().parents[1]
if str(项目根目录) not in sys.path:
    sys.path.insert(0, str(项目根目录))
