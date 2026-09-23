"""Supplementary Figure 2: reproducible study-selection flow diagram."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from mapper import configure_matplotlib, save_figure


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _box(
    ax,
    x: float,
    y: float,
    text: str,
    *,
    width: float = 0.68,
    height: float = 0.09,
    included: bool = False,
) -> None:
    color = "#D8F0E3" if included else "#E8F3F8"
    patch = FancyBboxPatch(
        (x - width / 2, y - height / 2),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.012",
        facecolor=color,
        edgecolor="#1F4E79",
        linewidth=1.4,
    )
    ax.add_patch(patch)
    ax.text(x, y, text, ha="center", va="center", fontsize=11.5, color="#18344A")


def build_selection_flow(root: Path) -> tuple[list[dict[str, object]], list[tuple[int, int]], str]:
    """Build count-reconciled nodes and edges without inventing missing screening stages."""
    data_dir = root / "data"
    included = pd.read_csv(data_dir / "included_study_order.csv")
    exclusions = pd.read_csv(data_dir / "post_extraction_exclusions.csv")
    form = pd.read_csv(data_dir / "reviewer_scoring_order.csv")

    include_flag = form["Include_In_Final_Corpus"].astype(str).str.casefold().isin(
        {"true", "1", "yes"}
    )
    if len(form) != 48 or int(include_flag.sum()) != len(included):
        raise ValueError("The 48-record reviewer form does not reconcile with the final corpus")

    source_form_id = pd.to_numeric(exclusions["Source_Form_Paper_ID"], errors="coerce")
    pre_scoring = exclusions.loc[source_form_id.isna()]
    post_scoring = exclusions.loc[source_form_id.notna()]
    if len(post_scoring) != int((~include_flag).sum()):
        raise ValueError("Post-scoring exclusions do not reconcile with the reviewer form")

    pre_counts = pre_scoring["Exclusion_Category"].value_counts().to_dict()
    post_counts = post_scoring["Exclusion_Category"].value_counts().to_dict()
    expected_pre = {"Not MRI modality": 3, "Review/survey only": 3, "Duplicate": 2}
    expected_post = {
        "Not MRI modality": 1,
        "Duplicate": 1,
        "No AI/DL method": 1,
    }
    if pre_counts != expected_pre or post_counts != expected_post:
        raise ValueError("Screening exclusions differ from the documented eligibility reconciliation")

    extracted = len(included) + len(exclusions)
    identified = 183
    no_recoverable_disposition = identified - extracted
    if no_recoverable_disposition < 0:
        raise ValueError("Structured-extraction count exceeds the identified-record count")

    nodes = [
        {"x": 0.5, "y": 0.93, "width": 0.68, "height": 0.085, "label": f"Records identified by database search\n(n = {identified})"},
        {
            "x": 0.25,
            "y": 0.75,
            "width": 0.42,
            "height": 0.17,
            "label": f"Records with no recoverable\nscreening disposition\n(n = {no_recoverable_disposition})\nStage not inferred",
        },
        {
            "x": 0.75,
            "y": 0.75,
            "width": 0.42,
            "height": 0.17,
            "label": f"Records with recoverable\nscreening disposition\n(n = {extracted})\n8 pre-scoring exclusions\n+ 48 scored",
        },
        {
            "x": 0.5,
            "y": 0.57,
            "width": 0.68,
            "height": 0.10,
            "label": f"Excluded before the all-author scoring form (n = {len(pre_scoring)})\n"
            f"{pre_counts['Not MRI modality']} non-MRI; {pre_counts['Review/survey only']} reviews/surveys;\n"
            f"{pre_counts['Duplicate']} duplicates",
        },
        {
            "x": 0.5,
            "y": 0.42,
            "width": 0.68,
            "height": 0.09,
            "label": f"Records independently scored by all 11\nreviewers (n = {len(form)})",
        },
        {
            "x": 0.5,
            "y": 0.255,
            "width": 0.68,
            "height": 0.13,
            "label": f"Excluded after scoring during eligibility\nreconciliation (n = {len(post_scoring)})\n"
            f"{post_counts['Duplicate']} duplicate preprint; {post_counts['Not MRI modality']} paper without an MRI\n"
            f"experiment; {post_counts['No AI/DL method']} method without AI/deep learning",
        },
        {"x": 0.5, "y": 0.09, "width": 0.68, "height": 0.09, "label": f"Final analytical corpus\n(n = {len(included)})"},
    ]
    edges = [(0, 1), (0, 2), (2, 3), (3, 4), (4, 5), (5, 6)]
    footnote = (
        "The archived export has no reliable stage label for 127 records; disposition is recoverable for 56.\n"
        "Screening stage is not inferred."
    )
    return nodes, edges, footnote


def create_figS2():
    configure_matplotlib()
    root = _project_root()
    nodes, edges, footnote = build_selection_flow(root)

    figure, ax = plt.subplots(figsize=(8, 7.2))
    ax.set_xlim(-0.04, 1.04)
    ax.set_ylim(-0.12, 1.02)
    ax.axis("off")
    ax.set_title(
        "Supplementary Figure 2. Study-selection flow",
        fontsize=16,
        fontweight="bold",
        color="#15324A",
        pad=12,
    )
    for index, node in enumerate(nodes):
        _box(
            ax,
            float(node["x"]),
            float(node["y"]),
            str(node["label"]),
            width=float(node["width"]),
            height=float(node["height"]),
            included=index == len(nodes) - 1,
        )

    # The first node branches to a terminal unknown-disposition group and to
    # the recoverable branch; only the latter continues through screening.
    split_y = 0.845
    ax.plot([0.5, 0.5], [float(nodes[0]["y"]) - float(nodes[0]["height"]) / 2, split_y], color="#56758A", lw=1.5)
    ax.plot([float(nodes[1]["x"]), float(nodes[2]["x"])], [split_y, split_y], color="#56758A", lw=1.5)
    for target in (1, 2):
        node = nodes[target]
        ax.annotate(
            "",
            xy=(float(node["x"]), float(node["y"]) + float(node["height"]) / 2),
            xytext=(float(node["x"]), split_y),
            arrowprops={"arrowstyle": "-|>", "color": "#56758A", "lw": 1.5},
        )
    for source, target in edges[2:]:
        from_node, to_node = nodes[source], nodes[target]
        start = (
            float(from_node["x"]),
            float(from_node["y"]) - float(from_node["height"]) / 2,
        )
        end = (
            float(to_node["x"]),
            float(to_node["y"]) + float(to_node["height"]) / 2,
        )
        if start[0] != end[0]:
            elbow_y = (start[1] + end[1]) / 2
            ax.plot([start[0], start[0]], [start[1], elbow_y], color="#56758A", lw=1.5)
            ax.plot([start[0], end[0]], [elbow_y, elbow_y], color="#56758A", lw=1.5)
            arrow_start = (end[0], elbow_y)
        else:
            arrow_start = start
        ax.annotate(
            "",
            xy=end,
            xytext=arrow_start,
            arrowprops={"arrowstyle": "-|>", "color": "#56758A", "lw": 1.5},
        )
    ax.text(
        0.5,
        -0.035,
        footnote,
        ha="center",
        va="center",
        fontsize=10.5,
        color="#5C6770",
        wrap=True,
    )
    save_figure(figure, "figS2_prisma_flow", output_dir=root / "figures" / "supplementary")
    return figure


if __name__ == "__main__":
    create_figS2()
