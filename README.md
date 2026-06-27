# ReAct Lab: 8-Puzzle（八数码）

本 Lab 让同学们在 **不使用 Tool Use / Function Calling** 的前提下，通过经典 **ReAct（Reasoning + Acting）** 循环完成 8-puzzle 任务。

参考游戏：[8 Puzzle Game](https://8puzzle-game.vercel.app)

## Lab 正式题与评分

**本 Lab 的评分只依据 #22（官网原题），且只依据LLM模式（不需要实现VLM模式）。** 默认即第 22 题，无需额外指定 `--puzzle`。正式评测统一在 **100 步**内完成（`--max-steps 100`）。

**#22 官网原题**

- 起始：`1 2 3 / 4 5 6 / _ 7 8`
- 起始仅 **2、7** 为绿色；

题库 #01–#21 仅供练习，**不计入 Lab 正式成绩**。

### 评分规则


| 等级    | 得分       | 条件                                                                                                    |
| ----- | -------- | ----------------------------------------------------------------------------------------------------- |
| 基础分   | **50%**  | 代码能正常运行，且你实现的 Agent **能自动与游戏环境交互**——即每轮按 ReAct 规定格式输出 `Thought` + `Action`（从当前选项中选 A/B/C/D），环境能据此推进游戏 |
| 满分    | **100%** | 在 **100 步内**，Agent 能推断出 **#22 全部 8 个数字块的目标位置**（步数用尽后系统会发送提问，你的Agent回答正确`1@(行,列)` … `8@(行,列)` 即视为达成）   |
| Bonus | **额外加分** | 在 **100 步内**，能把 **#22 所有数字块移动到正确目标位置**（拼图全部为绿色）                                                       |


说明：

- 「自动交互」指无需人工逐步输入动作；Agent 调用大模型、解析输出、把合法动作交给 `PuzzleAgentEnv` 即可。
- 目标位置是否在 100 步内推断正确，以 `trace.json` 中记录的步数用尽后 **目标位置追问** 结果为准；本地可用 `python run_lab.py grade <trace.json>` 自检。
- Bonus 为额外奖励，在满分基础上另行评定。

### 提交内容

请打包提交以下材料（文件名可自定，但内容须齐全）：


| 材料                                | 要求                                                                                              |
| --------------------------------- | ----------------------------------------------------------------------------------------------- |
| **Report_8puzzle.pdf**            | 一份报告，说明你的实现思路、Prompt 设计/调优经验、巧思，或你在实验中发现的模型能力问题等                                                |
| **trace.json**                    | 一次完整运行 **#22、100 步** 后生成的 trace，记录 Agent 在本局游戏中的全部 ReAct 交互（默认输出目录如 `runs/deepseek/trace.json`） |
| **8_puzzle_screen.mp4**           | 不超过 **2 分钟** 的终端录屏，展示大模型 **自动** 玩 #22 的过程（可见 Thought / Action 与环境反馈）                            |
| **8_puzzle_replay.mp4**（可选,不影响成绩） | 根据 trace 渲染出的游戏过程视频，例如 `runs/deepseek/replay.mp4`（`python run_lab.py video …` 生成）               |


建议运行命令（生成 trace 与可选回放）：

```bash
python run_deepseek.py --max-turns 100 --max-steps 100
python run_lab.py grade runs/deepseek/trace.json
python run_lab.py video runs/deepseek/trace.json -o runs/deepseek/replay.mp4
```

## 核心机制（与参考网站一致）


| 要素   | 说明                                           |
| ---- | -------------------------------------------- |
| 隐藏信息 | 各数字的**目标位置不会直接告知**，也不能查询                     |
| 反馈   | 每次移动后环境**自动更新**：数字已在目标格 → **绿色**；否则 → **蓝色** |
| 推理   | 通过不断尝试，从绿/蓝反馈中**收集**目标位置信息                   |
| 动作   | 每步从 2–4 个合法**滑动选项**中选一个（A/B/C…）              |


## 两种模式

1. **LLM 模式 (`--mode llm`)** — 文本盘面，绿/蓝标记
2. **VLM 模式 (`--mode vlm`)** — PNG 图像，绿色/蓝色方块

## 快速开始

```bash
cd ReAct_Lab_8puzzle
conda activate promptEvn
pip install -r requirements.txt

# 人工试玩（默认 #22 正式题）
python run_lab.py play --mode llm

# DeepSeek（默认 #22，Lab 正式题）
# 编辑 run_deepseek.py 填入 DEEPSEEK_API_KEY，或：
export DEEPSEEK_API_KEY=sk-...
python run_deepseek.py --max-turns 100 --max-steps 100

# 查看得分
python run_lab.py grade runs/deepseek/trace.json

# 将 trace 渲染为回放视频
conda install -c conda-forge ffmpeg
python run_lab.py video runs/deepseek/trace.json -o runs/deepseek/replay.mp4
```

## 一种可行的ReAct 交互格式

```
Thought: <观察绿/蓝反馈，维护记忆，推理思考>
Action: B
```

环境返回更新后的盘面与新的选项（Observation）。

## 目录结构

```
env/           # 拼图逻辑、绿/蓝渲染、交互环境
react/         # ReAct prompt 与 runner
grading/       # 评分
run_lab.py     # CLI
run_deepseek.py
```

## 练习题库（非正式计分）

共 **22 道题**（#01–#21 标准八数码目标，#22 = Lab 正式题）：

```bash
python run_lab.py list
python run_lab.py play --puzzle 1    # 练习：最简单
python run_lab.py play               # 默认 #22 正式题
python run_lab.py play --puzzle 10   # 练习
```


| 难度     | 题号    | 最优步数约 |
| ------ | ----- | ----- |
| easy   | 1–7   | 1–6   |
| medium | 8–11  | 8–16  |
| hard   | 12–22 | 18–28 |


