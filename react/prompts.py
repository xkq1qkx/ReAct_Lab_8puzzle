"""ReAct prompt templates for LLM and VLM modes."""

from __future__ import annotations

import re

SYSTEM_PROMPT = """\
你正在完成一个 8-puzzle（八数码）ReAct Lab。

游戏规则（与 https://8puzzle-game.vercel.app 一致）：
1. 盘面为 3×3，含数字 1-8 与一个空格。空格不能被直接移动；每次只能让与空格相邻的一个数字块滑入空格（数字块移到空格处，空格移到该块原位置）。
2. 试探「(r,c) 是否是数字 N 的目标」时，必须让 N 占据 (r,c) 后看绿/蓝——此时空格在其它格，不能与 N 同占 (r,c)。规划应围绕如何利用空格逐步把数字块送到待测位置。
3. 你不知道各数字的目标位置，也不能直接查询。
4. 每次移动后，环境会更新并反馈新状态：
   - 若某数字已在它的目标格，该格为绿色；
   - 否则该格为蓝色。
5. 你需要通过不断尝试，从绿/蓝反馈中推断各数字的目标位置，并做出越来越合理的移动。
6. **解题分两大步**：① 先推断出全部 8 个数字块的目标位置；② 再规划路线，利用空格把所有数字块搬到各自目标格。每步 Thought 应维护「已知目标位置」记忆（如 `1→(0,0)`，并标出尚未确认的数字），并说明当前处于哪一阶段。
7. **结合历史，避免重复**：回顾本局此前各步的盘面与尝试，推断目标位置后选择**新的、有信息增益**的动作；不要大量重复已经试过且无效的走法。
8. **绿色块有时也要动**：为把蓝色块送到目标格，可能需要暂时移走已绿色的块以让路；最终目标是全部变绿，不是「绿色块永远不动」。
9. 每步只能从环境「可选动作」中选择一个字母（通常 2–4 个，如 A/B 或 A/B/C/D）；作答前重新阅读当前列表，不要自创移动或沿用上一轮的字母含义。
10. **每轮必须输出完整 ReAct 回复**（Thought + Action），不允许空回复；无效动作（空输入、错误字母）不会移动盘面，但会浪费一步。
11. 使用 ReAct 格式，不要调用 function call / tool use。
12. 满分条件：将所有数字块移动到各自的目标位置；若步数用尽未完成，可回答 YES 并一次性提交 `1@(行,列)` … `8@(行,列)`，环境判定全部正确得 0.5 分。

ReAct 格式（Action 行只能是单个字母）：
Thought: <维护已知目标位置记忆；说明处于推断阶段还是搬运阶段；结合历史选择本步动作>
Action: <一个选项字母，如 A；必须来自当前「可选动作」列表>

坐标约定（用于 Thought 中记录推理）：行、列从 0 开始，左上角为 (0,0)。
"""

VLM_EXTRA = """\
当前观察包含盘面图像：绿色方块表示该数字已在目标位置，蓝色表示尚未到位。请结合图像推理。
"""


def build_user_message(observation: str, step: int) -> str:
    return f"Step {step}\n\n{observation}"


def extract_action(text: str) -> str:
    lines = text.strip().splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("action:"):
            payload = stripped.split(":", 1)[1].strip()
            letter = re.match(r"^([A-D])\b", payload.upper())
            if letter:
                return letter.group(1)
            return payload
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("thought:"):
            continue
        letter = re.match(r"^([A-D])\b", stripped.upper())
        if letter:
            return letter.group(1)
    return ""
