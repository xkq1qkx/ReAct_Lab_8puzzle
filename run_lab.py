#!/usr/bin/env python3
"""ReAct 8-Puzzle Lab — entry point."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from env.agent_env import PuzzleAgentEnv
from env.puzzle import EightPuzzle
from env.puzzle_bank import PUZZLE_COUNT, list_puzzles_text, make_config
from grading.goal_inquiry import collect_goals_batch_interactive
from grading.scorer import grade_puzzle
from react.runner import MockModel, OpenAICompatibleModel, run_react_episode, save_trace


def _load_env(mode: str, run_dir: str, puzzle_id: int, max_steps: int | None) -> PuzzleAgentEnv:
    config = make_config(puzzle_id=puzzle_id, max_steps=max_steps)
    return PuzzleAgentEnv(
        puzzle=EightPuzzle(config),
        mode=mode,
        run_dir=Path(run_dir),
    )


def cmd_play(args: argparse.Namespace) -> None:
    env = _load_env(args.mode, args.run_dir, args.puzzle, args.max_steps)
    result = env.reset()
    print(result.observation)
    if result.image_path:
        print(f"[图像已保存] {result.image_path}")

    ended_by_quit = False
    while not result.done:
        action = input("\nAction> ").strip()
        if action.lower() in {"quit", "q", "exit"}:
            ended_by_quit = True
            break
        result = env.step(action)
        print(f"\n--- 环境更新 ---\n{result.observation}")
        if args.mode == "vlm" and result.image_path:
            print(f"[图像] {result.image_path}")

    goal_submission = None
    if not ended_by_quit and not env.puzzle.is_solved():
        goal_submission = collect_goals_batch_interactive(env.puzzle)

    print("\n游戏结束。")
    print(grade_puzzle(env.puzzle, goal_submission).feedback)


def cmd_run(args: argparse.Namespace) -> None:
    env = _load_env(args.mode, args.run_dir, args.puzzle, args.max_steps)
    model = MockModel() if args.backend == "mock" else OpenAICompatibleModel(model=args.model)
    trace = run_react_episode(
        env,
        model,
        max_turns=args.max_turns,
        verbose=not args.quiet,
        goal_inquiry=not args.no_goal_inquiry,
    )
    out = Path(args.run_dir) / "trace.json"
    save_trace(trace, out)
    print(f"\nTrace saved to {out}")


def cmd_list(_: argparse.Namespace) -> None:
    print(list_puzzles_text())


def cmd_grade(args: argparse.Namespace) -> None:
    data = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    print(json.dumps(data.get("grade"), ensure_ascii=False, indent=2))


def cmd_video(args: argparse.Namespace) -> None:
    from react.trace_video import render_trace_video

    out = render_trace_video(
        Path(args.trace),
        output_path=Path(args.output) if args.output else None,
        fps=args.fps,
        width=args.width,
    )
    print(f"视频已保存: {out}")


def cmd_render(args: argparse.Namespace) -> None:
    config = make_config(puzzle_id=args.puzzle)
    puzzle = EightPuzzle(config)
    out = Path(args.output)
    from env.renderer import board_to_text, render_puzzle_image

    print(board_to_text(puzzle))
    render_puzzle_image(puzzle, output_path=out)
    print(f"\n示例图像: {out}")


def _add_puzzle_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--puzzle",
        type=int,
        default=22,
        help=f"题目编号 1–{PUZZLE_COUNT}（默认 22 = Lab 正式题）",
    )
    p.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="最大移动步数（默认随难度自动设置）",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ReAct 8-Puzzle Lab")
    sub = p.add_subparsers(dest="command", required=True)

    lst = sub.add_parser("list", help="列出全部题目")
    lst.set_defaults(func=cmd_list)

    play = sub.add_parser("play", help="人工交互模式")
    play.add_argument("--mode", choices=["llm", "vlm"], default="llm")
    play.add_argument("--run-dir", default="runs/manual")
    _add_puzzle_arg(play)
    play.set_defaults(func=cmd_play)

    run = sub.add_parser("run", help="运行 ReAct agent")
    run.add_argument("--mode", choices=["llm", "vlm"], default="llm")
    run.add_argument("--backend", choices=["mock", "openai"], default="mock")
    run.add_argument("--model", default="gpt-4o-mini")
    run.add_argument("--max-turns", type=int, default=40)
    run.add_argument("--run-dir", default="runs/react")
    run.add_argument("--quiet", action="store_true")
    run.add_argument(
        "--no-goal-inquiry",
        action="store_true",
        help="步数用尽后不进行目标位置追问",
    )
    _add_puzzle_arg(run)
    run.set_defaults(func=cmd_run)

    grade = sub.add_parser("grade", help="查看 trace 得分")
    grade.add_argument("trace", help="trace.json 路径")
    grade.set_defaults(func=cmd_grade)

    video = sub.add_parser("video", help="将 trace 渲染为 MP4 回放视频")
    video.add_argument("trace", help="trace.json 路径")
    video.add_argument("--output", "-o", help="输出 mp4 路径（默认同目录 trace.mp4）")
    video.add_argument("--fps", type=float, default=2.0, help="视频帧率")
    video.add_argument("--width", type=int, default=480, help="视频宽度（像素）")
    video.set_defaults(func=cmd_video)

    render = sub.add_parser("render", help="渲染示例盘面图像")
    render.add_argument("--output", default="assets/sample_board.png")
    _add_puzzle_arg(render)
    render.set_defaults(func=cmd_render)

    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
