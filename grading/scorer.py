"""Grading: solve (1.0) or correct goal map after failure (0.5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from env.puzzle import EightPuzzle, Position
from grading.goal_inquiry import goals_match


@dataclass
class GradeResult:
    total_score: float
    solved: bool
    steps: int
    feedback: str
    goals_known: bool = False
    goal_submission: Optional[Dict[int, Tuple[int, int]]] = None

    def to_dict(self) -> dict:
        payload = {
            "total_score": self.total_score,
            "solved": self.solved,
            "steps": self.steps,
            "goals_known": self.goals_known,
            "feedback": self.feedback,
        }
        if self.goal_submission is not None:
            payload["goal_submission"] = {
                str(tile): [pos[0], pos[1]]
                for tile, pos in sorted(self.goal_submission.items())
            }
        return payload


def grade_puzzle(
    puzzle: EightPuzzle,
    goal_submission: Optional[Dict[int, Position]] = None,
) -> GradeResult:
    solved = puzzle.is_solved()
    goals_known = False

    if solved:
        total = 1.0
        feedback = (
            f"拼图已全部到达目标位置。步数: {puzzle.steps}。"
            f"得分: {total:.2f}/1.00"
        )
    elif goal_submission is not None and goals_match(puzzle, goal_submission):
        goals_known = True
        total = 0.5
        feedback = (
            f"拼图尚未完成（已走 {puzzle.steps} 步），"
            f"但 8 个数字块的目标位置全部正确。"
            f"得分: {total:.2f}/1.00"
        )
    else:
        total = 0.0
        if goal_submission is not None:
            from grading.goal_inquiry import evaluate_goal_submission

            _, detail = evaluate_goal_submission(puzzle, goal_submission)
            feedback = (
                f"拼图尚未完成（已走 {puzzle.steps} 步），"
                f"且提交的目标位置不正确：{detail}"
                f"得分: {total:.2f}/1.00"
            )
        else:
            feedback = (
                f"拼图尚未完成（已走 {puzzle.steps} 步）。"
                f"得分: {total:.2f}/1.00"
            )

    return GradeResult(
        total_score=total,
        solved=solved,
        steps=puzzle.steps,
        feedback=feedback,
        goals_known=goals_known,
        goal_submission=goal_submission,
    )
