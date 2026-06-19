"""Grading: full score only when puzzle is solved via moves."""

from __future__ import annotations

from dataclasses import dataclass

from env.puzzle import EightPuzzle


@dataclass
class GradeResult:
    total_score: float
    solved: bool
    steps: int
    feedback: str

    def to_dict(self) -> dict:
        return {
            "total_score": self.total_score,
            "solved": self.solved,
            "steps": self.steps,
            "feedback": self.feedback,
        }


def grade_puzzle(puzzle: EightPuzzle) -> GradeResult:
    solved = puzzle.is_solved()
    total = 1.0 if solved else 0.0

    if solved:
        feedback = (
            f"拼图已全部到达目标位置。步数: {puzzle.steps}。"
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
    )
