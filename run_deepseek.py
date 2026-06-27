#!/usr/bin/env python3
"""
用 DeepSeek API 与 8-puzzle 环境进行 ReAct 交互。

用法：
  1. 在下方填入 DEEPSEEK_API_KEY，或 export DEEPSEEK_API_KEY=sk-...
  2. conda activate promptEvn
  3. python run_deepseek.py

可选参数见 --help。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from env.agent_env import PuzzleAgentEnv
from env.puzzle import EightPuzzle
from env.puzzle_bank import make_config, PUZZLE_COUNT
from react.deepseek_prompts import DEEPSEEK_SYSTEM_PROMPT
from react.prompts import build_user_message, extract_action
from grading.scorer import grade_puzzle
from react.runner import ReActTrace, run_goal_inquiry, save_trace
from react.trace_replay import board_to_json

# ============ 在这里填入你的 API Key ============
DEEPSEEK_API_KEY = ""
# ================================================

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-pro"


class DeepSeekModel:
    def __init__(
        self,
        api_key: str,
        model: str = DEEPSEEK_MODEL,
        base_url: str = DEEPSEEK_BASE_URL,
        temperature: float = 0.2,
    ):
        if not api_key:
            raise ValueError(
                "请设置 DeepSeek API Key：\n"
                "  1) 编辑 run_deepseek.py 中的 DEEPSEEK_API_KEY\n"
                "  2) 或 export DEEPSEEK_API_KEY=sk-..."
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("请先安装: pip install openai") from exc

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature

    def complete(self, messages: List[Dict[str, Any]], mode: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        msg = resp.choices[0].message
        content = (msg.content or "").strip()
        if not content:
            # deepseek-reasoner 有时把推理放在 reasoning_content，content 为空
            reasoning = getattr(msg, "reasoning_content", None) or ""
            content = reasoning.strip()
        return content


def build_deepseek_messages(
    history: List[Dict[str, Any]],
    observation: str,
    step: int,
) -> List[Dict[str, Any]]:
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": DEEPSEEK_SYSTEM_PROMPT}
    ]
    for item in history:
        messages.append({"role": "user", "content": item["observation"]})
        messages.append({"role": "assistant", "content": item["response"]})
    messages.append(
        {"role": "user", "content": build_user_message(observation, step)}
    )
    return messages


def run_deepseek_react(
    env: PuzzleAgentEnv,
    model: DeepSeekModel,
    max_turns: int = 60,
    verbose: bool = True,
    goal_inquiry: bool = True,
) -> ReActTrace:
    trace = ReActTrace()
    result = env.reset()
    history: List[Dict[str, Any]] = []
    trace.meta = {
        "puzzle_id": env.puzzle.config.puzzle_id,
        "start": board_to_json(env.puzzle.config.start),
        "goal": board_to_json(env.puzzle.config.goal),
        "max_steps": env.puzzle.config.max_steps,
    }

    if verbose:
        print("=" * 60)
        print("DeepSeek ReAct Loop — LLM 模式")
        print(f"Model: {model.model}")
        print("=" * 60)
        print("\n--- 初始 Observation ---\n")
        print(result.observation)

    for turn in range(max_turns):
        messages = build_deepseek_messages(history, result.observation, turn)
        response = model.complete(messages, env.mode)
        action = extract_action(response)

        if verbose:
            print(f"\n{'=' * 60}\nTurn {turn}\n{'-' * 60}")
            print(response)
            print(f"\n-> 解析 Action: {action!r}")

        history.append({"observation": result.observation, "response": response})
        trace.steps.append(
            {
                "turn": turn,
                "observation": result.observation,
                "response": response,
                "action": action,
            }
        )

        result = env.step(action)
        if verbose:
            print(f"\n--- 环境更新 ---\n{result.observation}")

        if result.done:
            break

    goal_submission = None
    if goal_inquiry and not env.puzzle.is_solved():
        goal_submission, trace.goal_inquiry = run_goal_inquiry(
            env.puzzle,
            model,
            env.mode,
            verbose=verbose,
            system_prompt=DEEPSEEK_SYSTEM_PROMPT,
            history=history,
        )

    trace.final_grade = grade_puzzle(env.puzzle, goal_submission)
    if verbose:
        print(f"\n{'=' * 60}\n{trace.final_grade.feedback}")
    return trace


def main() -> None:
    parser = argparse.ArgumentParser(description="DeepSeek ReAct 8-puzzle")
    parser.add_argument("--max-turns", type=int, default=60, help="最大 ReAct 轮数")
    parser.add_argument("--puzzle", type=int, default=22, help=f"题目编号 1–{PUZZLE_COUNT}（默认 22 = Lab 正式题）")
    parser.add_argument("--model", default=DEEPSEEK_MODEL, help="DeepSeek 模型名")
    parser.add_argument("--max-steps", type=int, default=None, help="环境最大移动步数（默认随难度）")
    parser.add_argument("--run-dir", default="runs/deepseek", help="trace 输出目录")
    parser.add_argument("--quiet", action="store_true", help="少打印中间过程")
    parser.add_argument(
        "--no-goal-inquiry",
        action="store_true",
        help="步数用尽后不进行目标位置追问",
    )
    args = parser.parse_args()

    api_key = DEEPSEEK_API_KEY or os.getenv("DEEPSEEK_API_KEY", "")
    model = DeepSeekModel(api_key=api_key, model=args.model)

    config = make_config(puzzle_id=args.puzzle, max_steps=args.max_steps)
    env = PuzzleAgentEnv(
        puzzle=EightPuzzle(config),
        mode="llm",
        run_dir=Path(args.run_dir),
    )

    trace = run_deepseek_react(
        env,
        model,
        max_turns=args.max_turns,
        verbose=not args.quiet,
        goal_inquiry=not args.no_goal_inquiry,
    )

    out = Path(args.run_dir) / "trace.json"
    save_trace(trace, out)
    print(f"\nTrace 已保存: {out}")


if __name__ == "__main__":
    main()
