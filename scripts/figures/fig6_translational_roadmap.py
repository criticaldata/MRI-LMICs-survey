"""Figure 6: evidence-linked roadmap from the 45-study corpus to deployment."""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

from mapper import configure_matplotlib, load_data, save_figure

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))
from review_metrics import add_derived_fields  # noqa: E402


def _card(ax, x, y, width, height, title, lines, color):
    card = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.014,rounding_size=0.016",
        facecolor=color,
        edgecolor="#24445C",
        linewidth=1.2,
    )
    ax.add_patch(card)
    ax.text(x + width / 2, y + height - 0.055, title, ha="center", va="center",
            fontsize=12, fontweight="bold", color="#15324A")
    ax.text(x + 0.035, y + height - 0.11, "\n".join(f"• {line}" for line in lines),
            ha="left", va="top", fontsize=9.4, color="#263C4A", linespacing=1.5)


def create_fig6():
    configure_matplotlib()
    data = add_derived_fields(load_data())
    n = len(data)
    tr_counts = {
        "Low-field domain": int(data["TR_LowFieldDomain"].sum()),
        "Open science": int(data["TR_OpenScience"].sum()),
        "Clinical evaluation": int(data["TR_ClinicalEvaluation"].sum()),
        "Hardware awareness": int(data["TR_HardwareAwareness"].sum()),
        "Data diversity": int(data["TR_DataDiversity"].sum()),
    }

    figure, ax = plt.subplots(figsize=(15, 8.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Figure 6. Translational roadmap for MRI enhancement in LMIC settings",
                 fontsize=17, fontweight="bold", color="#15324A", pad=20)
    ax.text(0.5, 0.94,
            f"Evidence base: {n} included MRI enhancement and SR-adjacent studies; mean TR = {data['TR_Score'].mean():.2f}/5",
            ha="center", fontsize=10.5, color="#52616B")

    _card(
        ax, 0.04, 0.54, 0.27, 0.32, "Current evidence",
        [
            f"Low-field domain: {tr_counts['Low-field domain']}/{n}",
            f"Open science: {tr_counts['Open science']}/{n}",
            f"Clinical evaluation: {tr_counts['Clinical evaluation']}/{n}",
            f"Hardware awareness: {tr_counts['Hardware awareness']}/{n}",
            f"Data diversity: {tr_counts['Data diversity']}/{n}",
        ], "#E8F3F8"
    )
    _card(
        ax, 0.365, 0.54, 0.27, 0.32, "Translation barriers",
        [
            "Limited evidence at ≤64 mT",
            "Heterogeneous reference construction",
            "Few public code/model releases",
            "No explicit inference requirements",
            "Sparse prospective LMIC validation",
        ], "#FCE9E7"
    )
    _card(
        ax, 0.69, 0.54, 0.27, 0.32, "Minimum reporting package",
        [
            "Input/target field and resolution",
            "Pairing and ground-truth provenance",
            "Device-specific inference resources",
            "Persistent code/model URL",
            "Clinical task and reader evaluation",
        ], "#F8F1DE"
    )
    _card(
        ax, 0.12, 0.13, 0.22, 0.25, "Technical",
        ["Cross-field/domain-shift testing", "External scanner/vendor validation", "Resource-aware model design"],
        "#E7F2FC"
    )
    _card(
        ax, 0.39, 0.13, 0.22, 0.25, "Clinical",
        ["Prospective LMIC cohorts", "Multi-reader diagnostic tasks", "Failure and uncertainty analysis"],
        "#E5F5EB"
    )
    _card(
        ax, 0.66, 0.13, 0.22, 0.25, "Implementation",
        ["Open code and model weights", "Local governance and maintenance", "Site-specific cost/workflow studies"],
        "#F1EAF8"
    )
    for x0, x1 in [(0.31, 0.365), (0.635, 0.69)]:
        ax.annotate("", xy=(x1, 0.70), xytext=(x0, 0.70),
                    arrowprops={"arrowstyle": "-|>", "lw": 1.8, "color": "#56758A"})
    ax.text(0.5, 0.055,
            "Goal: evidence-based deployment readiness—not performance claims based solely on PSNR/SSIM.",
            ha="center", fontsize=10.5, fontweight="bold", color="#24445C")

    save_figure(figure, "fig6_translational_roadmap")
    return figure


if __name__ == "__main__":
    create_fig6()
