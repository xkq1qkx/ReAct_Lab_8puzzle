"""Smoke tests for the 8-puzzle lab."""

from env.agent_env import PuzzleAgentEnv
from env.puzzle import EightPuzzle
from env.puzzle_bank import PUZZLE_COUNT, get_puzzle_spec, make_config
from grading.scorer import grade_puzzle


def test_puzzle_bank_count():
    assert PUZZLE_COUNT == 22


def test_website_puzzle():
    spec = get_puzzle_spec(22)
    puzzle = EightPuzzle(make_config(puzzle_id=22))
    assert puzzle.tiles_at_goal() == [2, 7]
    assert puzzle.goal == spec.goal
    assert EightPuzzle.is_solvable(puzzle.config.start, puzzle.config.goal)


def test_puzzle_bank_ordered():
    specs = [get_puzzle_spec(i) for i in range(1, PUZZLE_COUNT + 1)]
    assert specs[0].optimal_moves <= specs[-1].optimal_moves


def test_initial_green_tiles():
    puzzle = EightPuzzle(make_config(puzzle_id=6))
    assert puzzle.tiles_at_goal() == [1, 2, 3, 4, 7]


def test_move_labels_use_tile_direction():
    puzzle = EightPuzzle()
    labels = {m.label() for m in puzzle.legal_moves()}
    assert "将数字 3 向下滑动" in labels
    assert "将数字 5 向上滑动" in labels
    assert "将数字 8 向右滑动" in labels


def test_invalid_action():
    env = PuzzleAgentEnv(mode="llm")
    env.reset()
    r = env.step("INQUIRE 8")
    assert "无效动作" in r.message


def test_observation_includes_coordinates():
    env = PuzzleAgentEnv(mode="llm")
    env.reset()
    obs = env.last_result.observation
    assert "空格 @" in obs
    assert "数字 1 @ (0, 0)" in obs
    assert "绿色（已在目标位置）" in obs or "蓝色（尚未在目标位置）" in obs


def test_move_updates_observation():
    env = PuzzleAgentEnv(mode="llm")
    env.reset()
    letter = env.last_result.choices[0].letter
    r = env.step(letter)
    assert "已执行" in r.message
    assert "绿" in r.observation or "蓝" in r.observation
    assert env.puzzle.steps == 1


def test_grade_solved():
    puzzle = EightPuzzle()
    puzzle.board = [row[:] for row in puzzle.goal]
    g = grade_puzzle(puzzle)
    assert g.total_score == 1.0
    assert g.solved


def test_grade_unsolved():
    g = grade_puzzle(EightPuzzle())
    assert g.total_score == 0.0
    assert not g.solved
