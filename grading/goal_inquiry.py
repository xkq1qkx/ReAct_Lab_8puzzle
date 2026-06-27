"""Post-game goal-position inquiry when the puzzle is not solved."""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Tuple

from env.puzzle import EightPuzzle, Position

GOAL_INQUIRY_HINT = """\
【步数用尽后的补分环节】
若你在本局 Thought 里已推断出全部 8 个数字块各自的目标坐标，应回答 YES，并提交完整映射。
8 个数字各占 3×3 盘面中的一个不同格子（空格格不必提交）。"""

GOAL_YES_NO_PROMPT = """\
步数已用尽，拼图尚未完成。

你是否已经推断出全部 8 个数字块（1–8）各自的目标坐标？
若本局 Thought 中的【已知目标】已覆盖 1–8，请回答 YES；否则回答 NO。
只回复 YES 或 NO。"""

GOAL_SUBMISSION_PROMPT = """\
请一次性提交 8 个数字块的目标位置映射，每行一个，格式如下：

1@(行,列)
2@(行,列)
...
8@(行,列)

说明：
- 行、列从 0 开始，左上角为 (0,0)，右下角为 (2,2)
- 8 个坐标两两不同，分别对应数字 1–8 的目标格（不必提交空格位置）
- 也接受 `1 @ (行, 列)` 写法"""

GOAL_LINE_RE = re.compile(
    r"(?:数字\s*)?([1-8])\s*[@:：]\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)"
)
COORD_ONLY_RE = re.compile(r"\(\s*(\d+)\s*,\s*(\d+)\s*\)")


def parse_yes_no(text: str) -> Optional[bool]:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return None
    for candidate in (lines[0], lines[-1], text.strip()):
        c = candidate.upper().replace("。", "").replace("：", ":").strip()
        if c in {"YES", "Y", "是"} or c.startswith("YES"):
            return True
        if c in {"NO", "N", "否"} or c.startswith("NO"):
            return False
    return None


def parse_goal_line(text: str, expected_tile: Optional[int] = None) -> Optional[Tuple[int, Position]]:
    text = text.strip()
    if not text:
        return None

    match = GOAL_LINE_RE.search(text)
    if match:
        tile = int(match.group(1))
        pos = (int(match.group(2)), int(match.group(3)))
        if expected_tile is not None and tile != expected_tile:
            return None
        if not _valid_pos(pos):
            return None
        return tile, pos

    if expected_tile is not None:
        coord = COORD_ONLY_RE.search(text)
        if coord:
            pos = (int(coord.group(1)), int(coord.group(2)))
            if _valid_pos(pos):
                return expected_tile, pos
    return None


def parse_goal_submission(text: str) -> Optional[Dict[int, Position]]:
    goals: Dict[int, Position] = {}
    for line in text.splitlines():
        parsed = parse_goal_line(line)
        if parsed is None:
            continue
        tile, pos = parsed
        goals[tile] = pos
    if len(goals) != 8:
        return None
    if len(set(goals.values())) != 8:
        return None
    return goals


def _valid_pos(pos: Position) -> bool:
    r, c = pos
    return 0 <= r < 3 and 0 <= c < 3


def validate_goal_submission(submission: Dict[int, Position]) -> List[str]:
    errors: List[str] = []
    missing = [str(n) for n in range(1, 9) if n not in submission]
    if missing:
        errors.append(f"缺少数字: {', '.join(missing)}")
    for tile, pos in submission.items():
        if not _valid_pos(pos):
            errors.append(f"数字 {tile} 的坐标 {pos} 无效")
    positions = list(submission.values())
    if len(positions) != len(set(positions)):
        errors.append("8 个数字的目标坐标不能重复")
    return errors


def goals_match(puzzle: EightPuzzle, submission: Dict[int, Position]) -> bool:
    expected = puzzle.goal_positions()
    return all(submission.get(tile) == expected.get(tile) for tile in range(1, 9))


def evaluate_goal_submission(
    puzzle: EightPuzzle, submission: Dict[int, Position]
) -> Tuple[bool, str]:
    errors = validate_goal_submission(submission)
    if errors:
        return False, "；".join(errors)

    expected = puzzle.goal_positions()
    wrong = [
        f"{tile}→提交{submission[tile]}，应为{expected[tile]}"
        for tile in range(1, 9)
        if submission.get(tile) != expected.get(tile)
    ]
    if wrong:
        return False, "以下目标位置不正确：" + "；".join(wrong)
    return True, "8 个数字块的目标位置全部正确。"


def collect_goals_batch_interactive(
    puzzle: EightPuzzle,
    ask_yes_no: Callable[[str], str] = input,
    ask_block: Callable[[str], str] = input,
) -> Optional[Dict[int, Position]]:
    answer = ask_yes_no(f"\n{GOAL_YES_NO_PROMPT}\n> ").strip()
    if parse_yes_no(answer) is not True:
        return None

    print(GOAL_SUBMISSION_PROMPT)
    while True:
        text = ask_block("请一次性输入 8 行（可粘贴）:\n")
        goals = parse_goal_submission(text)
        if goals is None:
            print("  格式不完整或坐标重复。示例：1@(0,0)")
            continue
        ok, msg = evaluate_goal_submission(puzzle, goals)
        print(f"  {msg}")
        if ok:
            return goals
        print("  请修正后重新提交。")
