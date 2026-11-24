"""Smoke test: every dashboard section renders in both languages without errors.

Run:  python -m pytest tests/
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SECTIONS = ["📊  Market Overview", "💰  Pricing Strategy",
            "🎯  Scent Gaps & Product Moat", "📢  Customer Pain Points & Ad Hooks"]


@pytest.mark.parametrize("section", SECTIONS)
@pytest.mark.parametrize("lang", ["English", "العربية"])
def test_section_renders(section, lang):
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.sidebar.radio[0].set_value(section)
    at.sidebar.radio[1].set_value(lang)
    at.run()
    assert not at.exception, at.exception
