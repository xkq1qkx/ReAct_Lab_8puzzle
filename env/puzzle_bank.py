"""22 curated 8-puzzle instances, ordered easy → hard (by optimal move count)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from env.puzzle import Board, DEFAULT_GOAL, DEFAULT_START, PuzzleConfig

# https://8puzzle-game.vercel.app — fixed start & custom goal from site author
WEBSITE_START: Board = [
    [1, 2, 3],
    [4, 5, 6],
    [None, 7, 8],
]

WEBSITE_GOAL: Board = [
    [3, 2, 1],
    [6, 4, 5],
    [8, 7, None],
]


@dataclass(frozen=True)
class PuzzleSpec:
    id: int
    name: str
    start: Board
    tier: str
    optimal_moves: int
    greens_at_start: int
    description: str
    goal: Board = field(default_factory=lambda: [row[:] for row in DEFAULT_GOAL])


def _board(rows: List[List[Optional[int]]]) -> Board:
    return [row[:] for row in rows]


PUZZLE_BANK: List[PuzzleSpec] = [
    PuzzleSpec(1, "一步完成", _board([[1, 2, 3], [4, 5, None], [7, 8, 6]]), "easy", 1, 7, "仅差一步，熟悉绿色反馈"),
    PuzzleSpec(2, "两步还原", _board([[1, 2, 3], [4, None, 6], [7, 5, 8]]), "easy", 2, 6, "两步即可，注意空格位置"),
    PuzzleSpec(3, "小试牛刀", _board([[1, 2, 3], [None, 5, 6], [4, 7, 8]]), "easy", 3, 5, "3 步最优，开始规划"),
    PuzzleSpec(4, "初阶推理", _board([[None, 1, 2], [4, 5, 3], [7, 8, 6]]), "easy", 4, 4, "空格在左上角"),
    PuzzleSpec(5, "角块交换", _board([[1, 3, 6], [4, 2, None], [7, 5, 8]]), "easy", 5, 3, "仅 3 个绿色，需要试探"),
    PuzzleSpec(6, "Lab 默认题", DEFAULT_START, "easy", 5, 5, "课程默认起始布局"),
    PuzzleSpec(7, "底部归位", _board([[1, 2, 3], [7, 4, 5], [8, 6, None]]), "easy", 6, 3, "6 步最优，底部数字需调整"),
    PuzzleSpec(8, "中段整理", _board([[1, 3, 5], [4, None, 6], [7, 2, 8]]), "medium", 8, 4, "8 步最优，中等规划"),
    PuzzleSpec(9, "全盘打乱 I", _board([[3, 1, 6], [2, None, 5], [4, 7, 8]]), "medium", 12, 0, "无绿色提示，需从零推断"),
    PuzzleSpec(10, "全盘打乱 II", _board([[2, 3, 5], [7, None, 1], [8, 6, 4]]), "medium", 14, 0, "14 步最优"),
    PuzzleSpec(11, "交叉换位", _board([[2, 7, 3], [8, None, 4], [1, 5, 6]]), "medium", 16, 1, "16 步最优"),
    PuzzleSpec(12, "左上角挑战", _board([[None, 3, 1], [7, 4, 2], [8, 6, 5]]), "hard", 18, 0, "18 步最优，空格在角上"),
    PuzzleSpec(13, "深层搜索 I", _board([[4, 5, 2], [1, None, 3], [8, 7, 6]]), "hard", 18, 0, "18 步最优，数字排列高度打乱"),
    PuzzleSpec(14, "深层搜索 II", _board([[None, 7, 4], [5, 2, 1], [8, 6, 3]]), "hard", 18, 0, "18 步最优，另一种 18 步局面"),
    PuzzleSpec(15, "远程搬运", _board([[2, 4, 5], [3, 7, None], [1, 6, 8]]), "hard", 21, 0, "21 步最优"),
    PuzzleSpec(16, "高难 I", _board([[4, 6, None], [2, 1, 8], [5, 3, 7]]), "hard", 22, 0, "22 步最优"),
    PuzzleSpec(17, "高难 II", _board([[None, 8, 1], [6, 3, 2], [7, 4, 5]]), "hard", 22, 1, "22 步最优，仅 1 个绿色"),
    PuzzleSpec(18, "高难 III", _board([[7, 8, 3], [1, 6, 2], [5, 4, None]]), "hard", 22, 1, "22 步最优，右下角空格"),
    PuzzleSpec(19, "专家 I", _board([[1, 7, None], [3, 6, 8], [4, 5, 2]]), "hard", 24, 1, "24 步最优"),
    PuzzleSpec(20, "专家 II", _board([[None, 1, 7], [6, 4, 2], [5, 3, 8]]), "hard", 24, 0, "24 步最优，左上角空格"),
    PuzzleSpec(21, "终极挑战", _board([[7, 5, 6], [8, None, 4], [3, 2, 1]]), "hard", 26, 0, "26 步最优"),
    PuzzleSpec(
        22,
        "官网原题",
        WEBSITE_START,
        "hard",
        28,
        2,
        "8puzzle-game.vercel.app 固定起始盘 + 非标准目标布局",
        goal=WEBSITE_GOAL,
    ),
]

PUZZLE_COUNT = len(PUZZLE_BANK)


def get_puzzle_spec(puzzle_id: int) -> PuzzleSpec:
    if puzzle_id < 1 or puzzle_id > PUZZLE_COUNT:
        raise ValueError(f"题目编号应为 1–{PUZZLE_COUNT}，收到: {puzzle_id}")
    return PUZZLE_BANK[puzzle_id - 1]


def make_config(puzzle_id: int = 22, max_steps: Optional[int] = None) -> PuzzleConfig:
    spec = get_puzzle_spec(puzzle_id)
    if max_steps is None:
        if spec.tier == "easy":
            max_steps = 40
        elif spec.tier == "medium":
            max_steps = 60
        elif spec.id == 22:
            max_steps = 100
        else:
            max_steps = 80
    return PuzzleConfig(
        start=[row[:] for row in spec.start],
        goal=[row[:] for row in spec.goal],
        max_steps=max_steps,
        puzzle_id=spec.id,
    )


def list_puzzles_text() -> str:
    lines = [
        f"共 {PUZZLE_COUNT} 道题（#01–#21 目标为标准八数码，#22 为官网原题）：",
        "",
    ]
    for spec in PUZZLE_BANK:
        goal_tag = " [自定义目标]" if spec.goal != DEFAULT_GOAL else ""
        lines.append(
            f"  #{spec.id:02d} [{spec.tier:6s}] 最优≈{spec.optimal_moves:2d}步 | "
            f"起始绿色 {spec.greens_at_start} 块 | {spec.name}{goal_tag} — {spec.description}"
        )
    return "\n".join(lines)
