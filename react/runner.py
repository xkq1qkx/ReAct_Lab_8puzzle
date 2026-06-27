"""ReAct loop with OpenAI-compatible LLM / VLM backends."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from env.agent_env import PuzzleAgentEnv
from grading.goal_inquiry import (
    GOAL_INQUIRY_HINT,
    GOAL_SUBMISSION_PROMPT,
    GOAL_YES_NO_PROMPT,
    evaluate_goal_submission,
    parse_goal_submission,
    parse_yes_no,
)
from grading.scorer import GradeResult, grade_puzzle
from react.prompts import (
    SYSTEM_PROMPT,
    VLM_EXTRA,
    build_user_message,
    extract_action,
)
from react.trace_replay import board_to_json


@dataclass
class ReActTrace:
    steps: List[Dict[str, Any]] = field(default_factory=list)
    goal_inquiry: List[Dict[str, Any]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    final_grade: Optional[GradeResult] = None


class MockModel:
    """Offline demo agent for testing without API keys."""

    def __init__(self):
        self._turn = 0

    def complete(self, messages: List[Dict[str, Any]], mode: str) -> str:
        self._turn += 1
        if self._turn <= 3:
            return "Thought: 先观察绿/蓝反馈，尝试移动。\nAction: B"
        return "Thought: 继续根据绿色信息调整。\nAction: A"


class OpenAICompatibleModel:
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("Install openai: pip install openai") from exc

        self.client = OpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
        )
        self.model = model

    def complete(self, messages: List[Dict[str, Any]], mode: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""


def build_messages(
    history: List[Dict[str, Any]],
    observation: str,
    step: int,
    mode: str,
    image_base64: Optional[str] = None,
) -> List[Dict[str, Any]]:
    system = SYSTEM_PROMPT + ("\n" + VLM_EXTRA if mode == "vlm" else "")
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system}]

    for item in history:
        messages.append({"role": "user", "content": item["observation"]})
        messages.append({"role": "assistant", "content": item["response"]})

    user_text = build_user_message(observation, step)
    if mode == "vlm" and image_base64:
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                ],
            }
        )
    else:
        messages.append({"role": "user", "content": user_text})

    return messages


def run_goal_inquiry(
    puzzle: EightPuzzle,
    model: Any,
    mode: str,
    verbose: bool = True,
    system_prompt: str = SYSTEM_PROMPT,
    history: Optional[List[Dict[str, Any]]] = None,
) -> tuple[Optional[Dict[int, tuple[int, int]]], List[Dict[str, Any]]]:
    """Ask the agent to submit all 8 goal positions after an unsolved game."""
    trace: List[Dict[str, Any]] = []
    history = history or []

    def respond(prompt: str) -> str:
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": f"{system_prompt}\n\n{GOAL_INQUIRY_HINT}"}
        ]
        for item in history:
            messages.append({"role": "user", "content": item["observation"]})
            messages.append({"role": "assistant", "content": item["response"]})
        messages.append({"role": "user", "content": prompt})
        response = model.complete(messages, mode)
        if verbose:
            print(f"\n--- 目标位置询问 ---\n{prompt}\n---\n{response}")
        trace.append({"prompt": prompt, "response": response})
        return response

    yes_no_reply = respond(GOAL_YES_NO_PROMPT)
    if parse_yes_no(yes_no_reply) is not True:
        return None, trace

    for attempt in range(3):
        reply = respond(GOAL_SUBMISSION_PROMPT)
        goals = parse_goal_submission(reply)
        if goals is None:
            if verbose:
                print("  未能解析 8 行目标映射，请使用 1@(行,列) 格式。")
            continue
        ok, msg = evaluate_goal_submission(puzzle, goals)
        trace.append({"validation": msg, "correct": ok})
        if verbose:
            print(f"  环境判定: {msg}")
        if ok:
            return goals, trace
        reply_retry = respond(
            f"提交的目标位置不正确：{msg}\n"
            f"请修正后重新一次性提交 8 行，格式：1@(行,列) … 8@(行,列)"
        )
        goals = parse_goal_submission(reply_retry)
        if goals is not None:
            ok, msg = evaluate_goal_submission(puzzle, goals)
            trace.append({"validation": msg, "correct": ok})
            if verbose:
                print(f"  环境判定: {msg}")
            if ok:
                return goals, trace
    return None, trace


def run_react_episode(
    env: PuzzleAgentEnv,
    model: Any,
    max_turns: int = 40,
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

    for turn in range(max_turns):
        messages = build_messages(
            history,
            result.observation,
            turn,
            env.mode,
            result.image_base64,
        )
        response = model.complete(messages, env.mode)
        action = extract_action(response)

        if verbose:
            print(f"\n{'=' * 60}\nTurn {turn}\n{'-' * 60}")
            print(response)
            print(f"-> Parsed action: {action!r}")

        history.append({"observation": result.observation, "response": response})
        board_before = board_to_json(env.puzzle.board)
        puzzle_step_before = env.puzzle.steps

        result = env.step(action)
        valid_move = result.message.startswith("已执行")
        move_label = ""
        if valid_move:
            move_label = result.message.removeprefix("已执行: ").split("。")[0]

        trace.steps.append(
            {
                "turn": turn,
                "observation": history[-1]["observation"],
                "response": response,
                "action": action,
                "image_path": str(result.image_path) if result.image_path else None,
                "board_before": board_before,
                "board_after": board_to_json(env.puzzle.board),
                "puzzle_step_before": puzzle_step_before,
                "puzzle_step": env.puzzle.steps,
                "valid_move": valid_move,
                "move_label": move_label,
            }
        )

        if verbose:
            print(f"\n--- 环境更新 ---\n{result.observation}")

        if result.done:
            break

    goal_submission = None
    if goal_inquiry and not env.puzzle.is_solved():
        goal_submission, trace.goal_inquiry = run_goal_inquiry(
            env.puzzle, model, env.mode, verbose=verbose, history=history
        )

    trace.final_grade = grade_puzzle(env.puzzle, goal_submission)
    if verbose:
        print(f"\n{'=' * 60}\n{trace.final_grade.feedback}")
    return trace


def save_trace(trace: ReActTrace, path: Path) -> None:
    payload = {
        "meta": trace.meta,
        "steps": trace.steps,
        "goal_inquiry": trace.goal_inquiry,
        "grade": trace.final_grade.to_dict() if trace.final_grade else None,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
