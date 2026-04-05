"""
Figure 1: PRISMA Flow Diagram (SVG -> PNG conversion)

The authoritative PRISMA diagram is the hand-crafted SVG at
figures/main/fig1_prisma_flow.svg.  This script converts it to a PNG
at figures/main/png/fig1_prisma_flow.png for use in submissions that
require raster formats.
"""

import subprocess
from pathlib import Path


def _project_root():
    return Path(__file__).resolve().parent.parent.parent


def convert_prisma():
    root = _project_root()
    svg_path = root / "figures" / "main" / "fig1_prisma_flow.svg"
    png_dir = root / "figures" / "main" / "png"
    png_dir.mkdir(parents=True, exist_ok=True)
    png_path = png_dir / "fig1_prisma_flow.png"

    if not svg_path.exists():
        raise FileNotFoundError(f"SVG not found: {svg_path}")

    # Try rsvg-convert first (best quality, available via librsvg / brew)
    try:
        subprocess.run(
            ["rsvg-convert", "-d", "300", "-p", "300",
             str(svg_path), "-o", str(png_path)],
            check=True, capture_output=True,
        )
    except FileNotFoundError:
        # Fallback to cairosvg Python binding
        from cairosvg import svg2png
        svg2png(url=str(svg_path), write_to=str(png_path), dpi=300)

    print(f"\n=== Figure 1: PRISMA Flow ===")
    print(f"  Source: {svg_path.relative_to(root)}")
    print(f"  Saved:  {png_path.relative_to(root)}")


if __name__ == "__main__":
    convert_prisma()
