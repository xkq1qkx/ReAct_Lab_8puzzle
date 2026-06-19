"""ReAct loop with OpenAI-compatible LLM / VLM backends."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from env.agent_env import PuzzleAgentEnv
from grading.scorer import GradeResult, grade_puzzle
from react.prompts import (
    SYSTEM_PROMPT,
    VLM_EXTRA,
    build_user_message,
    extract_action,
)


@dataclass
class ReActTrace:
    steps: List[Dict[str, Any]] = field(default_factory=list)
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


def run_react_episode(
    env: PuzzleAgentEnv,
    model: Any,
    max_turns: int = 40,
    verbose: bool = True,
) -> ReActTrace:
    trace = ReActTrace()
    result = env.reset()
    history: List[Dict[str, Any]] = []

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
        trace.steps.append(
            {
                "turn": turn,
                "observation": result.observation,
                "response": response,
                "action": action,
                "image_path": str(result.image_path) if result.image_path else None,
            }
        )

        result = env.step(action)
        if verbose:
            print(f"\n--- 环境更新 ---\n{result.observation}")

        if result.done:
            break

    trace.final_grade = grade_puzzle(env.puzzle)
    if verbose:
        print(f"\n{'=' * 60}\n{trace.final_grade.feedback}")
    return trace


def save_trace(trace: ReActTrace, path: Path) -> None:
    payload = {
        "steps": trace.steps,
        "grade": trace.final_grade.to_dict() if trace.final_grade else None,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
