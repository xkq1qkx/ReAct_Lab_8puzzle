"""Render a ReAct trace as an MP4 replay video."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

from env.puzzle import EightPuzzle, PuzzleConfig
from env.puzzle_bank import make_config
from env.renderer import render_puzzle_image
from react.trace_replay import (
    TraceFrame,
    board_from_json,
    frames_from_trace,
    load_trace,
    parse_puzzle_id,
)


def _load_goal(meta: dict, puzzle_id: int):
    if meta.get("goal"):
        return board_from_json(meta["goal"])
    return make_config(puzzle_id=puzzle_id).goal


def render_frame(
    frame: TraceFrame,
    puzzle_id: int,
    goal,
    width: int = 480,
) -> Image.Image:
    config = PuzzleConfig(
        start=frame.board,
        goal=goal,
        puzzle_id=puzzle_id,
    )
    puzzle = EightPuzzle(config)
    puzzle.board = [row[:] for row in frame.board]
    puzzle.steps = frame.puzzle_step

    base = render_puzzle_image(puzzle)
    caption_h = 72
    canvas = Image.new("RGB", (base.width, base.height + caption_h), "#0f172a")
    canvas.paste(base, (0, caption_h))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except OSError:
        font = ImageFont.load_default()
        sub = font

    draw.text((16, 10), f"#{puzzle_id:02d} · 步数 {frame.puzzle_step}", fill="#e2e8f0", font=font)
    draw.text((16, 38), frame.caption[:120], fill="#94a3b8", font=sub)
    if width != canvas.width:
        ratio = width / canvas.width
        canvas = canvas.resize((width, int(canvas.height * ratio)), Image.Resampling.LANCZOS)
    return canvas


def write_mp4(frames: List[Image.Image], output_path: Path, fps: float = 2.0) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if _write_mp4_imageio(frames, output_path, fps):
        return
    if _write_mp4_ffmpeg_cli(frames, output_path, fps):
        return
    raise RuntimeError(
        "无法生成 MP4。请在 conda 环境中任选一种方式安装：\n"
        "  pip install imageio imageio-ffmpeg\n"
        "  conda install -c conda-forge ffmpeg\n"
        "  conda install -c conda-forge imageio-ffmpeg"
    )


def _write_mp4_imageio(frames: List[Image.Image], output_path: Path, fps: float) -> bool:
    try:
        import numpy as np
        import imageio.v3 as iio
    except ImportError:
        return False

    try:
        arrays = [np.asarray(img.convert("RGB")) for img in frames]
        iio.imwrite(
            output_path,
            arrays,
            fps=fps,
            codec="libx264",
            pixelformat="yuv420p",
        )
        return True
    except Exception:
        return False


def _write_mp4_ffmpeg_cli(frames: List[Image.Image], output_path: Path, fps: float) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        try:
            import imageio_ffmpeg

            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except (ImportError, RuntimeError):
            return False

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i, img in enumerate(frames):
            img.save(tmp_path / f"frame_{i:04d}.png")
        try:
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-framerate",
                    str(fps),
                    "-i",
                    str(tmp_path / "frame_%04d.png"),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(output_path),
                ],
                check=True,
                capture_output=True,
            )
            return True
        except (subprocess.CalledProcessError, OSError):
            return False


def render_trace_video(
    trace_path: Path,
    output_path: Optional[Path] = None,
    fps: float = 2.0,
    width: int = 480,
) -> Path:
    data = load_trace(trace_path)
    meta, replay_frames = frames_from_trace(data)
    puzzle_id = int(meta["puzzle_id"]) if meta.get("puzzle_id") else parse_puzzle_id(
        data["steps"][0]["observation"]
    )
    goal = _load_goal(meta, puzzle_id)
    images = [
        render_frame(frame, puzzle_id=puzzle_id, goal=goal, width=width)
        for frame in replay_frames
    ]

    if output_path is None:
        output_path = trace_path.with_suffix(".mp4")
    write_mp4(images, output_path, fps=fps)
    return output_path
