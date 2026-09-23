from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "figures"))

from figS2_prisma_flow import build_selection_flow, create_figS2  # noqa: E402


def test_pre_scoring_exclusions_and_scored_records_are_sibling_outcomes():
    _, edges, _ = build_selection_flow(REPO)
    assert edges == [(0, 1), (0, 2), (2, 3), (2, 4), (4, 5), (5, 6)]


def test_prisma_flow_remains_legible_at_full_page_width():
    figure = create_figS2()
    try:
        assert figure.get_figwidth() <= 8.0
        labels = [text for text in figure.axes[0].texts if text.get_text().strip()]
        assert labels
        assert min(text.get_fontsize() for text in labels) >= 10.0
        figure.canvas.draw()
        boxes = [patch for patch in figure.axes[0].patches if isinstance(patch, FancyBboxPatch)]
        for box, text in zip(boxes, figure.axes[0].texts[: len(boxes)], strict=True):
            box_bounds = box.get_window_extent()
            text_bounds = text.get_window_extent(renderer=figure.canvas.get_renderer())
            assert text_bounds.x0 >= box_bounds.x0 + 10
            assert text_bounds.x1 <= box_bounds.x1 - 10
            assert text_bounds.y0 >= box_bounds.y0 + 6
            assert text_bounds.y1 <= box_bounds.y1 - 6
        footnote = labels[-1]
        bounds = footnote.get_window_extent(renderer=figure.canvas.get_renderer())
        assert bounds.x0 >= figure.bbox.width * 0.05
        assert bounds.x1 <= figure.bbox.width * 0.95
    finally:
        plt.close(figure)


def test_prisma_flow_connectors_do_not_run_diagonally():
    figure = create_figS2()
    try:
        figure.canvas.draw()
        arrows = [
            text.arrow_patch
            for text in figure.axes[0].texts
            if getattr(text, "arrow_patch", None) is not None
        ]
        assert arrows
        for arrow in arrows:
            bounds = arrow.get_path().get_extents()
            assert bounds.width / bounds.height <= 1.0
    finally:
        plt.close(figure)


def test_arrowheads_leave_visible_clearance_before_node_boxes():
    figure = create_figS2()
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        boxes = [patch.get_window_extent(renderer) for patch in figure.axes[0].patches]
        arrows = [
            text.arrow_patch
            for text in figure.axes[0].texts
            if getattr(text, "arrow_patch", None) is not None
        ]
        assert arrows
        # The six arrows point to nodes 1 through 6 in the declared flow graph.
        for arrow_index, (arrow, target_index) in enumerate(zip(arrows, range(1, 7), strict=True)):
            arrow_bounds = arrow.get_window_extent(renderer)
            target_bounds = boxes[target_index]
            assert arrow_bounds.y0 > target_bounds.y1 + 3, (
                f"arrow {arrow_index} has no visible gap before target node {target_index}: "
                f"arrow={arrow_bounds}, node={target_bounds}"
            )
            assert abs(arrow_bounds.x0 + arrow_bounds.width / 2 - (target_bounds.x0 + target_bounds.width / 2)) < 3
    finally:
        plt.close(figure)


def test_sibling_outcome_boxes_are_visibly_separated():
    figure = create_figS2()
    try:
        figure.canvas.draw()
        renderer = figure.canvas.get_renderer()
        pre_scoring_exclusions, scored_records = [
            patch.get_window_extent(renderer) for patch in figure.axes[0].patches[3:5]
        ]
        assert pre_scoring_exclusions.x0 - scored_records.x1 >= 12
    finally:
        plt.close(figure)
