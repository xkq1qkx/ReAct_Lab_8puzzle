"""Rebuild board frames from a saved ReAct trace."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from env.agent_env import ChoiceAction
from env.puzzle import Board, EightPuzzle, MoveAction
from env.puzzle_bank import make_config

PUZZLE_ID_RE = re.compile(r"当前题目:\s*#(\d+)")
BLANK_RE = re.compile(r"空格 @ \((\d+), (\d+)\)")
TILE_RE = re.compile(r"数字 (\d+) @ \((\d+), (\d+)\)")


@dataclass
class TraceFrame:
    puzzle_step: int
    turn: Optional[int]
    board: Board
    caption: str
    action: str = ""


def board_from_json(raw: List[List[Optional[int]]]) -> Board:
    return [row[:] for row in raw]


def board_to_json(board: Board) -> List[List[Optional[int]]]:
    return [row[:] for row in board]


def parse_puzzle_id(observation: str) -> int:
    match = PUZZLE_ID_RE.search(observation)
    if not match:
        raise ValueError("trace 中未找到题目编号（当前题目: #N）")
    return int(match.group(1))


def parse_board_from_observation(observation: str) -> Board:
    blank = BLANK_RE.search(observation)
    if blank is None:
        raise ValueError("observation 中未找到空格坐标")
    board: Board = [[None, None, None] for _ in range(3)]
    board[int(blank.group(1))][int(blank.group(2))] = None
    for tile, row, col in TILE_RE.findall(observation):
        board[int(row)][int(col)] = int(tile)
    return board


def _choices_for_puzzle(puzzle: EightPuzzle) -> List[ChoiceAction]:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return [
        ChoiceAction(letter=letters[i], description=move.label(), move=move)
        for i, move in enumerate(puzzle.legal_moves())
    ]


def _apply_letter(puzzle: EightPuzzle, letter: str) -> tuple[bool, str]:
    if not letter:
        return False, "空动作"
    choices = _choices_for_puzzle(puzzle)
    valid = {c.letter.upper() for c in choices}
    picked = letter.strip().upper()
    if len(picked) != 1 or picked not in valid:
        return False, f"无效动作: {letter!r}"

    move: Optional[MoveAction] = None
    for choice in choices:
        if choice.letter.upper() == picked:
            move = choice.move
            break
    assert move is not None
    if puzzle.apply_move(move):
        return True, move.label()
    return False, "非法移动"


def load_trace(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def frames_from_trace(data: Dict[str, Any]) -> tuple[Dict[str, Any], List[TraceFrame]]:
    """Return trace metadata and ordered board frames for video rendering."""
    meta = data.get("meta") or {}
    steps = data.get("steps") or []
    if not steps:
        raise ValueError("trace 中没有 steps")

    if meta.get("puzzle_id") and meta.get("goal"):
        puzzle_id = int(meta["puzzle_id"])
        config = make_config(puzzle_id=puzzle_id, max_steps=meta.get("max_steps"))
        config.start = board_from_json(meta["start"])
        config.goal = board_from_json(meta["goal"])
    else:
        puzzle_id = parse_puzzle_id(steps[0]["observation"])
        config = make_config(puzzle_id=puzzle_id)

    frames: List[TraceFrame] = []

    if meta.get("start") and any(step.get("board_after") for step in steps):
        start = board_from_json(meta["start"])
        frames.append(
            TraceFrame(
                puzzle_step=0,
                turn=0,
                board=start,
                caption="初始盘面",
            )
        )
        for step in steps:
            if step.get("board_after") is None:
                continue
            turn = step.get("turn")
            valid = step.get("valid_move", True)
            label = step.get("move_label") or step.get("action") or ""
            prefix = "已执行" if valid else "无效"
            frames.append(
                TraceFrame(
                    puzzle_step=int(step.get("puzzle_step", 0)),
                    turn=turn,
                    board=board_from_json(step["board_after"]),
                    caption=f"Turn {turn} · {prefix}: {label}",
                    action=str(step.get("action") or ""),
                )
            )
        return meta, frames

    if steps[0].get("board_before") is not None:
        for step in steps:
            turn = step.get("turn")
            if step.get("board_before") is not None:
                frames.append(
                    TraceFrame(
                        puzzle_step=int(step.get("puzzle_step_before", 0)),
                        turn=turn,
                        board=board_from_json(step["board_before"]),
                        caption=f"Turn {turn} · 步数 {step.get('puzzle_step_before', 0)}",
                        action="",
                    )
                )
            if step.get("board_after") is not None:
                label = step.get("move_label") or step.get("action") or ""
                valid = step.get("valid_move", True)
                prefix = "已执行" if valid else "无效"
                frames.append(
                    TraceFrame(
                        puzzle_step=int(step.get("puzzle_step", 0)),
                        turn=turn,
                        board=board_from_json(step["board_after"]),
                        caption=f"Turn {turn} · {prefix}: {label}",
                        action=str(step.get("action") or ""),
                    )
                )
        if frames:
            return meta or {"puzzle_id": puzzle_id}, frames

    puzzle = EightPuzzle(config)
    frames.append(
        TraceFrame(
            puzzle_step=0,
            turn=0,
            board=deepcopy(puzzle.board),
            caption="初始盘面",
        )
    )

    for step in steps:
        turn = step.get("turn", 0)
        action = str(step.get("action") or "")
        ok, label = _apply_letter(puzzle, action)
        if ok:
            frames.append(
                TraceFrame(
                    puzzle_step=puzzle.steps,
                    turn=turn,
                    board=deepcopy(puzzle.board),
                    caption=f"Turn {turn} · 已执行: {label}",
                    action=action,
                )
            )
        else:
            frames.append(
                TraceFrame(
                    puzzle_step=puzzle.steps,
                    turn=turn,
                    board=deepcopy(puzzle.board),
                    caption=f"Turn {turn} · {label}",
                    action=action,
                )
            )

    return meta or {"puzzle_id": puzzle_id}, frames
