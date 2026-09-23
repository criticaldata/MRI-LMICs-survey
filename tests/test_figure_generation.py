"""
Smoke tests for figure and table generation scripts.
"""

import sys
import subprocess
import os
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
FIGURES_DIR = SCRIPTS_DIR / "figures"
TABLES_DIR = SCRIPTS_DIR / "tables"

FIGURE_SCRIPTS = [
    "fig1_year_distribution.py",
    "fig2_architecture_distribution.py",
    "fig3_performance_comparison.py",
    "fig4_lmic_translational_gap.py",
    "fig5_field_strength_application.py",
    "fig6_translational_roadmap.py",
    "figS1_temporal_trends.py",
    "figS2_prisma_flow.py",
    "figS3_reviewer_score_distributions.py",
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


def test_master_generator_survives_legacy_windows_console_encoding():
    """The all-output runner must not crash printing Unicode child logs on Windows."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252:strict"
    env["PYTHONUTF8"] = "0"
    result = subprocess.run(
        [sys.executable, str(FIGURES_DIR / "generate_all_figures.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=180,
    )
    assert result.returncode == 0, f"Full generation failed:\n{result.stdout[-4000:]}\n{result.stderr[-4000:]}"
    assert "Tables: 15/15 successful" in result.stdout
    assert "Figures: 8/8 successful" in result.stdout


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
