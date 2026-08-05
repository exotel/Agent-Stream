#!/usr/bin/env python3
"""Root shim — delegates to integrations/openai-realtime (backward compatible).

Canonical OpenAI Realtime bot:
  cd integrations/openai-realtime && python main.py
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_OPENAI = _ROOT / "integrations" / "openai-realtime"

if not (_OPENAI / "main.py").is_file():
    print("Missing integrations/openai-realtime/main.py", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, str(_OPENAI))
runpy.run_path(str(_OPENAI / "main.py"), run_name="__main__")
