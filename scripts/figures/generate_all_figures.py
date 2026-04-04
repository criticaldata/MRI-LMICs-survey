"""
Master script to generate all figures and tables for the MRI-LMICs survey paper.
Run: python scripts/figures/generate_all_figures.py
"""

import sys
import time
import subprocess
from pathlib import Path

print("=" * 70)
print("MRI-LMICs SURVEY - FIGURE & TABLE GENERATION")
print("=" * 70)
print()

start_time = time.time()
task_times = {}
scripts_dir = Path(__file__).parent


def run_script(script_path, description):
    """Run a Python script and track timing."""
    print(f"\n{'='*70}")
    print(f"Generating: {description}")
    print(f"Script: {script_path.name}")
    print(f"{'='*70}")

    t0 = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, check=True,
        )
        elapsed = time.time() - t0
        task_times[description] = elapsed
        if result.stdout:
            print(result.stdout)
        print(f"\nDone in {elapsed:.2f}s")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


# --- Tables ---
print("\n" + "=" * 70)
print("GENERATING TABLES")
print("=" * 70)

tables_dir = scripts_dir.parent / "tables"
tables = [
    (tables_dir / "table1_study_characteristics.py", "Table 1: Study Characteristics"),
    (tables_dir / "table2_ai_architectures.py", "Table 2: AI Architectures"),
    (tables_dir / "table3_performance_metrics.py", "Table 3: Performance Metrics"),
    (tables_dir / "table4_lmic_applicability.py", "Table 4: LMIC Applicability"),
    (tables_dir / "table_merged_performance_lmic.py", "Table 2 (Main): Merged Performance & LMIC"),
    (tables_dir / "analysis_cross_field_generalization.py", "Analysis: Cross-Field Generalization"),
    (tables_dir / "analysis_edge_deployment.py", "Analysis: Edge Deployment Candidates"),
    (tables_dir / "analysis_reviewer_bias.py", "Analysis: Reviewer Bias / IRR Proxy"),
    (tables_dir / "analysis_temporal_trends.py", "Analysis: Temporal Trends"),
    (tables_dir / "analysis_translational_readiness.py", "Analysis: Translational Readiness"),
    (tables_dir / "analysis_dataset_diversity.py", "Analysis: Dataset Diversity"),
    (tables_dir / "analysis_quality_assessment.py", "Analysis: Quality Assessment"),
    (tables_dir / "analysis_non_mri_papers.py", "Analysis: Non-MRI Papers"),
    (tables_dir / "abstract_numbers.py", "Abstract Numbers Verification"),
    (tables_dir / "table5_statistical_insights.py", "Table 5: Statistical Insights"),
    (tables_dir / "table6_geographic_equity.py", "Table 6: Geographic Equity"),
]

table_ok = sum(run_script(path, desc) for path, desc in tables)

# --- Figures ---
print("\n" + "=" * 70)
print("GENERATING FIGURES")
print("=" * 70)

figures = [
    (scripts_dir / "fig1_prisma_flow.py", "Figure 1A: PRISMA Flow Diagram"),
    (scripts_dir / "fig1_year_distribution.py", "Figure 1B: Year Distribution"),
    (scripts_dir / "fig2_architecture_distribution.py", "Figure 2: Architecture Distribution"),
    (scripts_dir / "fig3_lmic_relevance.py", "Figure 3: LMIC Relevance"),
    (scripts_dir / "fig4_performance_comparison.py", "Figure 4: Performance Comparison"),
    (scripts_dir / "fig5_field_strength_application.py", "Figure 5: Field Strength & Application"),
    (scripts_dir / "figS1_temporal_trends.py", "Figure S1: Temporal Trends"),
]

fig_ok = sum(run_script(path, desc) for path, desc in figures)

# --- Summary ---
total_time = time.time() - start_time

print("\n" + "=" * 70)
print("GENERATION SUMMARY")
print("=" * 70)
print(f"\nTables: {table_ok}/{len(tables)} successful")
print(f"Figures: {fig_ok}/{len(figures)} successful")
print(f"\nTotal time: {total_time:.2f}s")

print("\nTiming breakdown:")
for desc, elapsed in sorted(task_times.items(), key=lambda x: x[1], reverse=True):
    print(f"  {desc}: {elapsed:.2f}s")

project_root = Path(__file__).parent.parent.parent
print(f"\nOutput directories:")
for d in ["tables", "figures/main/png", "figures/main/pdf"]:
    p = project_root / d
    if p.exists():
        files = list(p.glob("*"))
        print(f"  {d}/: {len(files)} files")

# --- Figure 6 PDF Conversion (Manual) ---
print("\n" + "=" * 70)
print("POST-PROCESSING: FIGURE 6 PDF CONVERSION")
print("=" * 70)
try:
    from PIL import Image
    png_path = project_root / "figures/main/png/fig6_translational_roadmap.png"
    pdf_path = project_root / "figures/main/pdf/fig6_translational_roadmap.pdf"
    
    if png_path.exists():
        print(f"Converting {png_path.name} to PDF...")
        image = Image.open(png_path)
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        image.save(pdf_path, "PDF", resolution=300.0)
        print(f"✓ Saved: {pdf_path.name}")
    else:
        print(f"⚠ Warning: {png_path.name} not found. Skipping conversion.")
except ImportError:
    print("⚠ Error: Pillow not installed. Cannot convert PNG to PDF.")
except Exception as e:
    print(f"⚠ Error converting Figure 6: {e}")

print("\n" + "=" * 70)
print("ALL DONE!")
print("=" * 70)
