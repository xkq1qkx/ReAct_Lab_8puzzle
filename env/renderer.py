"""Render puzzle state as text (LLM) or image (VLM)."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from env.puzzle import Board, EightPuzzle

GREEN = "#22c55e"
BLUE = "#2563eb"
BLANK_FILL = "#1e293b"
BG = "#0f172a"


def board_to_text(puzzle: EightPuzzle, title: str = "当前盘面") -> str:
    board = puzzle.board
    lines = [
        title,
        "（绿色=该数字已在目标位置，蓝色=尚未在目标位置）",
        "┌─────┬─────┬─────┐",
    ]
    for r in range(3):
        cells = []
        for c in range(3):
            val = board[r][c]
            if val is None:
                cells.append("     ")
            else:
                mark = "绿" if puzzle.tile_is_at_goal(r, c) else "蓝"
                cells.append(f"{mark}{val:>2} ")
        lines.append("│" + "│".join(cells) + "│")
        if r < 2:
            lines.append("├─────┼─────┼─────┤")
    lines.append("└─────┴─────┴─────┘")
    return "\n".join(lines)


def render_puzzle_image(
    puzzle: EightPuzzle,
    output_path: Optional[Path] = None,
) -> Image.Image:
    """Render board with green/blue tiles like the reference web game."""
    tile = 120
    gap = 8
    margin = 24
    size = margin * 2 + tile * 3 + gap * 2
    img = Image.new("RGB", (size, size + 40), BG)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 42)
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except OSError:
        font = ImageFont.load_default()
        title_font = font

    draw.text((margin, 8), "8 Puzzle — 绿色=已在目标位置", fill="#e2e8f0", font=title_font)

    origin_y = 40
    for r in range(3):
        for c in range(3):
            val = puzzle.board[r][c]
            x = margin + c * (tile + gap)
            y = origin_y + r * (tile + gap)

            if val is None:
                fill = BLANK_FILL
                text_fill = "#64748b"
            elif puzzle.tile_is_at_goal(r, c):
                fill = GREEN
                text_fill = "#052e16"
            else:
                fill = BLUE
                text_fill = "#eff6ff"

            draw.rounded_rectangle(
                [x, y, x + tile, y + tile],
                radius=14,
                fill=fill,
                outline="#334155",
                width=3,
            )

            if val is not None:
                text = str(val)
                bbox = draw.textbbox((0, 0), text, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                draw.text(
                    (x + (tile - tw) / 2, y + (tile - th) / 2 - 4),
                    text,
                    fill=text_fill,
                    font=font,
                )

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)

    return img


def image_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def board_coordinates_text(puzzle: EightPuzzle) -> str:
    """Human/LLM-friendly coordinate listing for each cell."""
    br, bc = puzzle.find_blank(puzzle.board)
    lines = [
        "坐标说明：行、列从 0 开始，左上角为 (0,0)，右下角为 (2,2)。",
        "位置清单：",
        f"  空格 @ ({br}, {bc})",
    ]
    for tile in range(1, 9):
        for r in range(3):
            for c in range(3):
                if puzzle.board[r][c] == tile:
                    if puzzle.tile_is_at_goal(r, c):
                        status = "绿色（已在目标位置）"
                    else:
                        status = "蓝色（尚未在目标位置）"
                    lines.append(f"  数字 {tile} @ ({r}, {c}) — {status}")
                    break
    return "\n".join(lines)


def render_observation_text(puzzle: EightPuzzle) -> str:
    at_goal = puzzle.tiles_at_goal()
    parts = [
        board_to_text(puzzle),
        "",
        board_coordinates_text(puzzle),
        "",
        f"已走步数: {puzzle.steps} / {puzzle.config.max_steps}",
        f"当前已在目标位置的数字: {', '.join(map(str, at_goal)) if at_goal else '（暂无）'}",
    ]
    if puzzle.is_solved():
        parts.append("状态: 所有数字块均已到达目标位置！")
    return "\n".join(parts)


def render_observation_image_path(puzzle: EightPuzzle, run_dir: Path) -> Path:
    path = run_dir / f"step_{puzzle.steps:03d}.png"
    render_puzzle_image(puzzle, output_path=path)
    return path
