from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "figures"))

from figS2_prisma_flow import create_figS2  # noqa: E402


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
            assert text_bounds.x0 >= box_bounds.x0 - 4
            assert text_bounds.x1 <= box_bounds.x1 + 4
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
