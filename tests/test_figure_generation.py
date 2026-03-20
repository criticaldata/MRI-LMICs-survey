"""
Smoke tests for figure and table generation scripts.
"""

import sys
import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
FIGURES_DIR = SCRIPTS_DIR / "figures"
TABLES_DIR = SCRIPTS_DIR / "tables"

FIGURE_SCRIPTS = [
    "fig1_year_distribution.py",
    "fig2_architecture_distribution.py",
    "fig3_lmic_relevance.py",
    "fig4_performance_comparison.py",
    "fig5_field_strength_application.py",
]

TABLE_SCRIPTS = [
    "table1_study_characteristics.py",
    "table2_ai_architectures.py",
    "table3_performance_metrics.py",
    "table4_lmic_applicability.py",
]


def test_all_figure_scripts_exist():
    for script in FIGURE_SCRIPTS:
        assert (FIGURES_DIR / script).exists(), f"Missing: {script}"


def test_all_table_scripts_exist():
    for script in TABLE_SCRIPTS:
        assert (TABLES_DIR / script).exists(), f"Missing: {script}"


def test_mapper_importable():
    sys.path.insert(0, str(FIGURES_DIR))
    import mapper
    assert hasattr(mapper, "load_data")
    assert hasattr(mapper, "save_figure")


@pytest.mark.parametrize("script_name", TABLE_SCRIPTS)
def test_table_generation(script_name):
    result = subprocess.run(
        [sys.executable, str(TABLES_DIR / script_name)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"{script_name} failed:\n{result.stderr}"


@pytest.mark.parametrize("script_name", FIGURE_SCRIPTS[:2])
def test_figure_generation_smoke(script_name):
    """Smoke test first 2 figures to catch import/data errors."""
    result = subprocess.run(
        [sys.executable, str(FIGURES_DIR / script_name)],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, f"{script_name} failed:\n{result.stderr}"
