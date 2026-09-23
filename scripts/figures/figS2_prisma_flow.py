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
        {"x": 0.5, "y": 0.94, "width": 0.68, "height": 0.08, "label": f"Records identified by database search\n(n = {identified})"},
        {
            "x": 0.25,
            "y": 0.745,
            "width": 0.42,
            "height": 0.15,
            "label": f"No recoverable screening\ndisposition\n(n = {no_recoverable_disposition})\nStage not inferred",
        },
        {
            "x": 0.75,
            "y": 0.745,
            "width": 0.42,
            "height": 0.15,
            "label": f"Disposition recoverable\n(n = {extracted})\n8 pre-scoring exclusions\n+ 48 scored",
        },
        {
            "x": 0.98,
            "y": 0.48,
            "width": 0.42,
            "height": 0.22,
            "label": f"Pre-scoring exclusions\n(n = {len(pre_scoring)})\n"
            f"{pre_counts['Not MRI modality']} non-MRI\n"
            f"{pre_counts['Review/survey only']} reviews/surveys\n"
            f"{pre_counts['Duplicate']} duplicates",
        },
        {
            "x": 0.5,
            "y": 0.48,
            "width": 0.42,
            "height": 0.22,
            "label": f"Scored independently\nby all 11 reviewers\n(n = {len(form)})",
        },
        {
            "x": 0.5,
            "y": 0.205,
            "width": 0.68,
            "height": 0.19,
            "label": f"Excluded during eligibility\nreconciliation after scoring (n = {len(post_scoring)})\n"
            f"{post_counts['Duplicate']} duplicate preprint\n"
            f"{post_counts['Not MRI modality']} paper without MRI experiment\n"
            f"{post_counts['No AI/DL method']} method without AI/deep learning",
        },
        {"x": 0.5, "y": -0.005, "width": 0.58, "height": 0.11, "label": f"Final analytical corpus\n(n = {len(included)})"},
    ]
    edges = [(0, 1), (0, 2), (2, 3), (2, 4), (4, 5), (5, 6)]
    footnote = (
        "The archived export has no reliable stage label for 127 records; disposition is recoverable for 56.\n"
        "Screening stage is not inferred."
    )
    return nodes, edges, footnote


def create_figS2():
    configure_matplotlib()
    root = _project_root()
    nodes, edges, footnote = build_selection_flow(root)

    figure, ax = plt.subplots(figsize=(8, 8.3))
    ax.set_xlim(-0.08, 1.23)
    ax.set_ylim(-0.23, 1.02)
    ax.axis("off")
    ax.set_title(
        "Supplementary Figure 2. Study-selection flow",
        fontsize=15.5,
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

    def draw_branch(source_index: int, target_indices: tuple[int, ...], split_y: float) -> None:
        source = nodes[source_index]
        source_bottom = float(source["y"]) - float(source["height"]) / 2
        source_x = float(source["x"])
        targets = [nodes[index] for index in target_indices]
        target_xs = [float(node["x"]) for node in targets]
        ax.plot(
            [source_x, source_x],
            [source_bottom - 0.012, split_y],
            color="#56758A",
            lw=1.5,
        )
        ax.plot(
            [min(target_xs), max(target_xs)],
            [split_y, split_y],
            color="#56758A",
            lw=1.5,
        )
        for node in targets:
            target_top = float(node["y"]) + float(node["height"]) / 2
            ax.annotate(
                "",
                xy=(float(node["x"]), target_top + 0.014),
                xytext=(float(node["x"]), split_y),
                arrowprops={
                    "arrowstyle": "-|>",
                    "color": "#56758A",
                    "lw": 1.5,
                    "mutation_scale": 12,
                    "shrinkA": 0,
                    "shrinkB": 0,
                },
            )

    # Unknown-disposition records are a terminal branch. Recoverable records
    # split into pre-scoring exclusions and the 48 records scored by all authors.
    draw_branch(0, (1, 2), split_y=0.865)
    draw_branch(2, (3, 4), split_y=0.64)
    for source, target in edges[4:]:
        from_node, to_node = nodes[source], nodes[target]
        start = (
            float(from_node["x"]),
            float(from_node["y"]) - float(from_node["height"]) / 2 - 0.012,
        )
        end = (
            float(to_node["x"]),
            float(to_node["y"]) + float(to_node["height"]) / 2 + 0.014,
        )
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops={
                "arrowstyle": "-|>",
                "color": "#56758A",
                "lw": 1.5,
                "mutation_scale": 12,
                "shrinkA": 0,
                "shrinkB": 0,
            },
        )
    ax.text(
        0.5,
        -0.15,
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
