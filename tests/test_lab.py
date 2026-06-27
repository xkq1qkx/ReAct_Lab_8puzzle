"""Smoke tests for the 8-puzzle lab."""

from env.agent_env import PuzzleAgentEnv
from env.puzzle import EightPuzzle
from env.puzzle_bank import PUZZLE_COUNT, get_puzzle_spec, make_config
from grading.goal_inquiry import goals_match, parse_goal_submission, parse_yes_no
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


def test_parse_goal_submission():
    text = "\n".join(
        f"{n} @ ({r}, {c})"
        for n, (r, c) in [
            (1, (0, 0)),
            (2, (0, 1)),
            (3, (0, 2)),
            (4, (1, 0)),
            (5, (1, 1)),
            (6, (1, 2)),
            (7, (2, 0)),
            (8, (2, 1)),
        ]
    )
    goals = parse_goal_submission(text)
    assert goals is not None
    puzzle = EightPuzzle()
    assert goals_match(puzzle, goals)


def test_grade_half_score_for_correct_goals():
    puzzle = EightPuzzle()
    submission = puzzle.goal_positions()
    g = grade_puzzle(puzzle, submission)
    assert g.total_score == 0.5
    assert g.goals_known
    assert not g.solved


def test_grade_wrong_goals():
    puzzle = EightPuzzle()
    g = grade_puzzle(puzzle, {1: (2, 2), 2: (0, 1), 3: (0, 2), 4: (1, 0), 5: (1, 1), 6: (1, 2), 7: (2, 0), 8: (2, 1)})
    assert g.total_score == 0.0
    assert not g.goals_known


def test_parse_goal_submission_compact_format():
    text = "\n".join(
        f"{n}@({r},{c})"
        for n, (r, c) in [
            (1, (0, 2)),
            (2, (0, 1)),
            (3, (0, 0)),
            (4, (1, 1)),
            (5, (1, 2)),
            (6, (1, 0)),
            (7, (2, 1)),
            (8, (2, 0)),
        ]
    )
    goals = parse_goal_submission(text)
    assert goals is not None
    from env.puzzle_bank import make_config

    puzzle = EightPuzzle(make_config(puzzle_id=22))
    assert goals_match(puzzle, goals)


def test_parse_yes_no():
    assert parse_yes_no("YES") is True
    assert parse_yes_no("Thought...\nNO") is False
    assert parse_yes_no("是") is True


def test_trace_replay_from_existing_trace():
    from pathlib import Path

    from react.trace_replay import frames_from_trace, load_trace

    data = load_trace(Path("runs/deepseek/trace.json"))
    meta, frames = frames_from_trace(data)
    assert frames[0].puzzle_step == 0
    assert len(frames) >= data["grade"]["steps"]
    assert frames[-1].puzzle_step == data["grade"]["steps"]
