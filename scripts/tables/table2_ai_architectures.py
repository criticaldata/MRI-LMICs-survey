"""
Table 2: AI Architectures Used

Generates a summary table of AI architectures, including the number of papers
using each type and representative models from the Architecture_Specifics field.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "figures"))

import pandas as pd
from mapper import load_data, get_project_root


def create_table2():
    df = load_data()

    # Group by normalized architecture
    arch_groups = df.groupby("Architecture_Norm")

    rows = []
    for arch_type, group in sorted(arch_groups, key=lambda x: -len(x[1])):
        n_papers = len(group)
        pct = n_papers / len(df) * 100

        # Collect representative models from Architecture_Specifics
        specifics = group["Architecture_Specifics"].dropna().unique()
        # Truncate long specifics for readability
        representative = []
        for s in specifics:
            if len(s) > 80:
                s = s[:77] + "..."
            representative.append(s)
        representative_str = "; ".join(representative[:4])
        if len(representative) > 4:
            representative_str += f" (+{len(representative)-4} more)"

        # Median PSNR and SSIM for this architecture
        psnr_vals = group["PSNR_Numeric"].dropna()
        ssim_vals = group["SSIM_Numeric"].dropna()
        psnr_str = f"{psnr_vals.median():.1f} dB (n={len(psnr_vals)})" if len(psnr_vals) > 0 else "N/R"
        ssim_str = f"{ssim_vals.median():.3f} (n={len(ssim_vals)})" if len(ssim_vals) > 0 else "N/R"

        rows.append({
            "Architecture Type": arch_type,
            "n Papers": n_papers,
            "% of Total": f"{pct:.1f}%",
            "Median PSNR": psnr_str,
            "Median SSIM": ssim_str,
            "Representative Models": representative_str,
        })

    result = pd.DataFrame(rows)

    # Save
    out_dir = get_project_root() / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_dir / "table2_ai_architectures.csv", index=False)

    # Print
    print("\n=== Table 2: AI Architectures Used ===\n")
    print(f"  {'Architecture':<15} {'n':>4} {'%':>7} {'Med. PSNR':>18} {'Med. SSIM':>16}")
    print(f"  {'-'*65}")
    for _, row in result.iterrows():
        print(f"  {row['Architecture Type']:<15} {row['n Papers']:>4} {row['% of Total']:>7} "
              f"{row['Median PSNR']:>18} {row['Median SSIM']:>16}")

    print(f"\n  Total papers: {len(df)}")
    return result


if __name__ == "__main__":
    create_table2()
