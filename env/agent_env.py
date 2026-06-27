"""Gym-like environment: multiple-choice slide actions + green/blue feedback."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from env.puzzle import EightPuzzle, MoveAction
from env.puzzle_bank import get_puzzle_spec
from env.renderer import (
    image_to_base64,
    render_observation_image_path,
    render_observation_text,
    render_puzzle_image,
)

INTRO = """\
欢迎来到 8-puzzle ReAct Lab。

你不知道每个数字块的最终目标位置，也无法直接查询。\
空格是唯一的空地，只能让相邻数字块滑入空格（空格本身不能当作棋子移动）。\
每次移动后，环境会告诉你新盘面：\
若某数字已在它的目标格，该格显示为绿色；否则为蓝色。\
请分两步解题：先推断全部 8 个数字块的目标位置，再规划路线把它们搬到位；\
每步思考时维护「已知目标位置」记忆。\
请结合本局已有尝试推断目标位置，做有效的新尝试，避免重复无效走法；\
必要时也可暂时移走绿色块，为其它块让路。\
每步请从下方「可选动作」中选一个字母回复，空输入或错误字母视为无效动作，盘面不会移动。\
若步数用尽仍未完成，系统会询问是否已知全部目标位置；若 YES，请一次性提交 `1@(行,列)` … `8@(行,列)`，环境判定正确可得 0.5 分。"""


@dataclass
class ChoiceAction:
    letter: str
    description: str
    move: MoveAction


@dataclass
class StepResult:
    observation: str
    image_path: Optional[Path] = None
    image_base64: Optional[str] = None
    choices: List[ChoiceAction] = field(default_factory=list)
    done: bool = False
    message: str = ""


class PuzzleAgentEnv:
    """8-puzzle environment for ReAct labs — move-only multiple choice."""

    def __init__(
        self,
        puzzle: Optional[EightPuzzle] = None,
        mode: str = "llm",
        run_dir: Optional[Path] = None,
    ):
        self.puzzle = puzzle or EightPuzzle()
        self.mode = mode.lower()
        if self.mode not in {"llm", "vlm"}:
            raise ValueError("mode must be 'llm' or 'vlm'")
        self.run_dir = run_dir or Path("runs/default")
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.last_result: Optional[StepResult] = None

    def reset(self) -> StepResult:
        self.puzzle = EightPuzzle(self.puzzle.config)
        spec = get_puzzle_spec(self.puzzle.config.puzzle_id)
        intro = (
            f"{INTRO}\n\n"
            f"当前题目: #{spec.id:02d} {spec.name}（{spec.tier}，最优约 {spec.optimal_moves} 步）"
        )
        return self._build_step(intro)

    def _format_choices(self, actions: List[ChoiceAction]) -> str:
        lines = ["可选动作（请选择一个选项字母）："]
        for act in actions:
            lines.append(f"  {act.letter}) {act.description}")
        return "\n".join(lines)

    def _build_actions(self) -> List[ChoiceAction]:
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return [
            ChoiceAction(letter=letters[i], description=move.label(), move=move)
            for i, move in enumerate(self.puzzle.legal_moves())
        ]

    def _build_step(self, message: str) -> StepResult:
        choices = self._build_actions()
        observation = (
            f"{message}\n\n{render_observation_text(self.puzzle)}\n\n"
            f"{self._format_choices(choices)}"
        )

        image_path = None
        image_b64 = None
        if self.mode == "vlm":
            image_path = render_observation_image_path(self.puzzle, self.run_dir)
            image_b64 = image_to_base64(render_puzzle_image(self.puzzle))

        result = StepResult(
            observation=observation,
            image_path=image_path,
            image_base64=image_b64,
            choices=choices,
            done=self.puzzle.done(),
            message=message,
        )
        self.last_result = result
        return result

    def _parse_selected_letter(self, action_text: str) -> Optional[str]:
        choices = self.last_result.choices if self.last_result else self._build_actions()
        valid = {c.letter.upper() for c in choices}
        text = action_text.strip()

        if len(text) == 1 and text.upper() in valid:
            return text.upper()

        match = re.search(r"\b([A-Z])\b", text.upper())
        if match and match.group(1) in valid:
            return match.group(1)
        return None

    def _choice_by_letter(self, letter: str) -> Optional[ChoiceAction]:
        choices = self.last_result.choices if self.last_result else self._build_actions()
        for choice in choices:
            if choice.letter.upper() == letter.upper():
                return choice
        return None

    def step(self, action_text: str) -> StepResult:
        action_text = action_text.strip()
        if not action_text:
            return self._build_step("无效动作：空输入。")

        letter = self._parse_selected_letter(action_text)
        if letter is None:
            return self._build_step(
                f"无效动作: {action_text!r}。请从当前滑动选项中选择一个字母。"
            )

        choice = self._choice_by_letter(letter)
        assert choice is not None

        if not self.puzzle.apply_move(choice.move):
            return self._build_step("非法移动（内部错误）。")

        msg = f"已执行: {choice.move.label()}"
        if self.puzzle.is_solved():
            msg += "。所有数字块均已到达目标位置！"
        return self._build_step(msg)
