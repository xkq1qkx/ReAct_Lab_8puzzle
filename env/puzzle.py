"""Core 8-puzzle logic: state, moves, goal, and solvability."""

from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

Position = Tuple[int, int]  # (row, col), 0-indexed
Board = List[List[Optional[int]]]

# Internal move direction follows blank movement; tile moves the opposite way.
OPPOSITE_DIRECTION = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}

DEFAULT_GOAL: Board = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, None],
]

DEFAULT_START: Board = [
    [1, 2, 3],
    [4, 8, None],
    [7, 6, 5],
]


@dataclass
class PuzzleConfig:
    start: Board = field(default_factory=lambda: deepcopy(DEFAULT_START))
    goal: Board = field(default_factory=lambda: deepcopy(DEFAULT_GOAL))
    max_steps: int = 80
    puzzle_id: int = 6


@dataclass
class MoveAction:
    """Slide a tile into the blank. `direction` is blank movement (internal)."""

    direction: str
    tile: int

    @property
    def tile_direction(self) -> str:
        return OPPOSITE_DIRECTION[self.direction]

    def label(self) -> str:
        dir_cn = {"UP": "上", "DOWN": "下", "LEFT": "左", "RIGHT": "右"}
        return f"将数字 {self.tile} 向{dir_cn[self.tile_direction]}滑动"


class EightPuzzle:
    DIRECTIONS = {
        "UP": (-1, 0),
        "DOWN": (1, 0),
        "LEFT": (0, -1),
        "RIGHT": (0, 1),
    }

    def __init__(self, config: Optional[PuzzleConfig] = None):
        self.config = config or PuzzleConfig()
        self.board: Board = deepcopy(self.config.start)
        self.goal: Board = deepcopy(self.config.goal)
        self.steps = 0
        self.history: List[str] = []

    @staticmethod
    def find_blank(board: Board) -> Position:
        for r in range(3):
            for c in range(3):
                if board[r][c] is None:
                    return (r, c)
        raise ValueError("Board has no blank cell")

    @staticmethod
    def flatten(board: Board) -> Tuple[Optional[int], ...]:
        return tuple(board[r][c] for r in range(3) for c in range(3))

    @staticmethod
    def inversion_count(board: Board) -> int:
        flat = [x for x in EightPuzzle.flatten(board) if x is not None]
        inv = 0
        for i in range(len(flat)):
            for j in range(i + 1, len(flat)):
                if flat[i] > flat[j]:
                    inv += 1
        return inv

    @classmethod
    def is_solvable(cls, start: Board, goal: Board) -> bool:
        return cls.inversion_count(start) % 2 == cls.inversion_count(goal) % 2

    def goal_positions(self) -> Dict[int, Position]:
        mapping: Dict[int, Position] = {}
        for r in range(3):
            for c in range(3):
                val = self.goal[r][c]
                if val is not None:
                    mapping[val] = (r, c)
        return mapping

    def tile_is_at_goal(self, row: int, col: int) -> bool:
        val = self.board[row][col]
        if val is None:
            return False
        return self.goal_positions().get(val) == (row, col)

    def tiles_at_goal(self) -> List[int]:
        found: List[int] = []
        for r in range(3):
            for c in range(3):
                val = self.board[r][c]
                if val is not None and self.tile_is_at_goal(r, c):
                    found.append(val)
        return sorted(found)

    def is_solved(self) -> bool:
        return self.flatten(self.board) == self.flatten(self.goal)

    def legal_moves(self) -> List[MoveAction]:
        br, bc = self.find_blank(self.board)
        moves: List[MoveAction] = []
        for direction, (dr, dc) in self.DIRECTIONS.items():
            nr, nc = br + dr, bc + dc
            if 0 <= nr < 3 and 0 <= nc < 3:
                tile = self.board[nr][nc]
                assert tile is not None
                moves.append(MoveAction(direction=direction, tile=tile))
        return moves

    def apply_move(self, action: MoveAction) -> bool:
        legal = {m.tile: m for m in self.legal_moves()}
        if action.tile not in legal or legal[action.tile].direction != action.direction:
            return False

        br, bc = self.find_blank(self.board)
        dr, dc = self.DIRECTIONS[action.direction]
        nr, nc = br + dr, bc + dc
        self.board[br][bc], self.board[nr][nc] = self.board[nr][nc], self.board[br][bc]
        self.steps += 1
        self.history.append(action.label())
        return True

    def done(self) -> bool:
        return self.is_solved() or self.steps >= self.config.max_steps

    @classmethod
    def random_solvable(cls, seed: Optional[int] = None) -> "EightPuzzle":
        rng = random.Random(seed)
        goal = deepcopy(DEFAULT_GOAL)
        while True:
            flat = list(range(1, 9))
            rng.shuffle(flat)
            start: Board = [
                [flat[0], flat[1], flat[2]],
                [flat[3], flat[4], flat[5]],
                [flat[6], flat[7], None],
            ]
            if cls.is_solvable(start, goal):
                return cls(PuzzleConfig(start=start, goal=goal))
        raise RuntimeError("unreachable")
