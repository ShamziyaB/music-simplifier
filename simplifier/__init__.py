"""Simplifier — помощник по упрощению нот для начинающих музыкантов."""

import os
import tempfile

# music21 подтягивает matplotlib; на сервере ему нужен безопасный backend и
# записываемый каталог для кэша (на Vercel доступен только /tmp).
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))

__version__ = "1.0.0"
