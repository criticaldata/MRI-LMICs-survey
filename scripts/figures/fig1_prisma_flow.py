"""
Figure 1 - Panel A: PRISMA-style Study Selection Flow Diagram

Shows the screening and selection process: 183 identified -> 48 included.
Uses matplotlib with clean box styling.
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from mapper import save_figure, configure_matplotlib

np.random.seed(42)

# Colors
BOX_BLUE = "#EBF5FB"
BORDER_BLUE = "#2E86AB"
BOX_RED = "#FDEDEC"
BORDER_RED = "#C73E1D"
BOX_GREEN = "#EAFAF1"
BORDER_GREEN = "#1E8449"
BOX_GRAY = "#F4F6F7"
BORDER_GRAY = "#95A5A6"
TEXT_DARK = "#1B2631"
ARROW_COLOR = "#5D6D7E"


def _draw_box(ax, x, y, w, h, text, fill, border, fontsize=10, bold=False):
    """Draw a rounded rectangle with centered text."""
    box = mpatches.FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.02",
        facecolor=fill, edgecolor=border, linewidth=1.8
    )
    ax.add_patch(box)
    weight = "bold" if bold else "normal"
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            fontweight=weight, color=TEXT_DARK, linespacing=1.4)


def _draw_arrow(ax, x1, y1, x2, y2):
    """Draw a downward arrow."""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=ARROW_COLOR,
                                lw=1.8, mutation_scale=15))


def _draw_side_arrow(ax, x1, y1, x2, y2):
    """Draw a side arrow (for exclusion boxes)."""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=BORDER_RED,
                                lw=1.5, mutation_scale=12))


def create_prisma():
    configure_matplotlib()
    fig, ax = plt.subplots(figsize=(10, 12))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Title
    ax.text(0.5, 0.97, "Study Selection Process",
            ha="center", va="top", fontsize=14, fontweight="bold", color=TEXT_DARK)
    ax.text(0.5, 0.94, "PRISMA-informed flow diagram for narrative review",
            ha="center", va="top", fontsize=10, color="#7f8c8d", style="italic")

    # ── IDENTIFICATION ──
    ax.text(0.03, 0.88, "IDENTIFICATION", fontsize=9, fontweight="bold",
            color=BORDER_BLUE, rotation=90, va="center")

    _draw_box(ax, 0.5, 0.87, 0.55, 0.06,
              "Records identified through database searching\n"
              "PubMed, IEEE Xplore, Scopus, Google Scholar\n"
              "(n = 183)",
              BOX_BLUE, BORDER_BLUE, fontsize=9.5, bold=True)

    _draw_arrow(ax, 0.5, 0.84, 0.5, 0.78)

    # ── SCREENING ──
    ax.text(0.03, 0.72, "SCREENING", fontsize=9, fontweight="bold",
            color=BORDER_BLUE, rotation=90, va="center")

    _draw_box(ax, 0.5, 0.76, 0.55, 0.05,
              "Records after duplicate removal (n = 172)",
              BOX_GRAY, BORDER_GRAY, fontsize=9.5)

    _draw_arrow(ax, 0.5, 0.735, 0.5, 0.68)

    # Exclusion 1
    _draw_box(ax, 0.5, 0.66, 0.55, 0.05,
              "Title and abstract screening (n = 172)",
              BOX_BLUE, BORDER_BLUE, fontsize=9.5)

    _draw_side_arrow(ax, 0.78, 0.66, 0.88, 0.66)
    _draw_box(ax, 0.92, 0.66, 0.14, 0.05,
              "Excluded\n(n = 68)",
              BOX_RED, BORDER_RED, fontsize=8)

    _draw_arrow(ax, 0.5, 0.635, 0.5, 0.58)

    # ── ELIGIBILITY ──
    ax.text(0.03, 0.52, "ELIGIBILITY", fontsize=9, fontweight="bold",
            color=BORDER_GREEN, rotation=90, va="center")

    _draw_box(ax, 0.5, 0.56, 0.55, 0.05,
              "Full-text articles assessed for eligibility (n = 104)",
              BOX_BLUE, BORDER_BLUE, fontsize=9.5)

    _draw_side_arrow(ax, 0.78, 0.56, 0.88, 0.56)

    _draw_box(ax, 0.92, 0.50, 0.14, 0.16,
              "Excluded (n = 56)\n\n"
              "Not SR-focused: 22\n"
              "Not MRI: 11\n"
              "Duplicate data: 7\n"
              "No AI/DL method: 6\n"
              "Review/survey: 5\n"
              "Conference abstract\n"
              "only: 5",
              BOX_RED, BORDER_RED, fontsize=7.5)

    _draw_arrow(ax, 0.5, 0.535, 0.5, 0.39)

    # ── INCLUSION ──
    ax.text(0.03, 0.32, "INCLUSION", fontsize=9, fontweight="bold",
            color=BORDER_GREEN, rotation=90, va="center")

    _draw_box(ax, 0.5, 0.37, 0.55, 0.06,
              "Studies included in narrative review\n"
              "(n = 48)",
              BOX_GREEN, BORDER_GREEN, fontsize=11, bold=True)

    _draw_arrow(ax, 0.5, 0.34, 0.5, 0.26)

    # Breakdown boxes
    breakdown_y = 0.22
    box_w = 0.22
    box_h = 0.14

    _draw_box(ax, 0.2, breakdown_y, box_w, box_h,
              "Brain MRI: 24\nMusculoskeletal: 7\nCardiac: 4\nOther: 13",
              BOX_BLUE, BORDER_BLUE, fontsize=8.5)
    ax.text(0.2, breakdown_y + box_h / 2 + 0.015, "By Application",
            ha="center", fontsize=8.5, fontweight="bold", color=BORDER_BLUE)

    _draw_box(ax, 0.5, breakdown_y, box_w, box_h,
              "CNN: 23\nU-Net: 11\nHybrid: 6\nGAN: 4\nOther: 4",
              "#FEF9E7", "#F18F01", fontsize=8.5)
    ax.text(0.5, breakdown_y + box_h / 2 + 0.015, "By Architecture",
            ha="center", fontsize=8.5, fontweight="bold", color="#F18F01")

    _draw_box(ax, 0.8, breakdown_y, box_w, box_h,
              "Low-field: 9\nStandard: 16\nMixed: 6\nNot specified: 16\nHigh-field: 1",
              "#EAFAF1", "#1E8449", fontsize=8.5)
    ax.text(0.8, breakdown_y + box_h / 2 + 0.015, "By Field Strength",
            ha="center", fontsize=8.5, fontweight="bold", color="#1E8449")

    # Split arrows to three breakdown boxes
    for target_x in [0.2, 0.5, 0.8]:
        _draw_arrow(ax, 0.5, 0.26, target_x, breakdown_y + box_h / 2 + 0.005)

    # Extraction team note
    ax.text(0.5, 0.08,
            "Data extracted by 11 independent reviewers using standardized 32-field template\n"
            "LMIC relevance scored 1\u20135  |  Quality flagged per paper  |  All extractions verified",
            ha="center", va="center", fontsize=9, color="#5D6D7E",
            style="italic", linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#F8F9F9",
                      edgecolor="#D5D8DC", linewidth=1))

    save_figure(fig, "fig1a_prisma_flow")

    print("\n=== Figure 1A: PRISMA Flow ===")
    print("  183 identified -> 172 after dedup -> 104 full-text -> 48 included")
    print("  Excluded: 68 screening + 56 eligibility = 124 total")

    return fig


if __name__ == "__main__":
    create_prisma()
