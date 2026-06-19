# ReAct Lab: 8-Puzzle（八数码）

本 Lab 让同学们在 **不使用 Tool Use / Function Calling** 的前提下，通过经典 **ReAct（Reasoning + Acting）** 循环完成 8-puzzle 任务。

参考游戏：[8 Puzzle Game](https://8puzzle-game.vercel.app)

## 核心机制（与参考网站一致）


| 要素   | 说明                                           |
| ---- | -------------------------------------------- |
| 隐藏信息 | 各数字的**目标位置不会直接告知**，也不能查询                     |
| 反馈   | 每次移动后环境**自动更新**：数字已在目标格 → **绿色**；否则 → **蓝色** |
| 推理   | 通过不断尝试，从绿/蓝反馈中**收集**目标位置信息                   |
| 动作   | 每步从 2–4 个合法**滑动选项**中选一个（A/B/C…）              |
| 得分   | **1.0 分**：将所有数字块移动到目标位置；否则 0 分               |


## 两种模式

1. **LLM 模式 (`--mode llm`)** — 文本盘面，绿/蓝标记
2. **VLM 模式 (`--mode vlm`)** — PNG 图像，绿色/蓝色方块

## 快速开始

```bash
cd ReAct_Lab_8puzzle
conda activate promptEvn
pip install -r requirements.txt

# 人工试玩
python run_lab.py play --mode llm

# 渲染示例（起始盘：1,2,3,4,7 为绿色）
python run_lab.py render --output assets/sample_board.png

# DeepSeek（LLM 模式 ReAct）
# 编辑 run_deepseek.py 填入 DEEPSEEK_API_KEY，或：
export DEEPSEEK_API_KEY=sk-...
python run_deepseek.py --puzzle 9 --max-turns 500 --max-steps 500
```

## ReAct 交互格式

```
Thought: <观察绿/蓝反馈，记录推断的目标位置>
Action: B
```

环境返回更新后的盘面与新的选项（Observation）。

## 得分

仅看最终是否完成拼图：

```bash
python run_lab.py grade runs/react/trace.json
```

## 目录结构

```
env/           # 拼图逻辑、绿/蓝渲染、交互环境
react/         # ReAct prompt 与 runner
grading/       # 评分
run_lab.py     # CLI
```

## 题库

共 **22 道题**（#01–#21 标准八数码目标，**#22 = [官网原题](https://8puzzle-game.vercel.app)**）：

```bash
python run_lab.py list
python run_lab.py play --puzzle 1    # 最简单
python run_lab.py play --puzzle 22   # 官网原题（自定义目标）
python run_deepseek.py --puzzle 10
```


| 难度     | 题号    | 最优步数约 |
| ------ | ----- | ----- |
| easy   | 1–7   | 1–6   |
| medium | 8–11  | 8–16  |
| hard   | 12–22 | 18–28 |


**#22 官网原题**

- 起始：`1 2 3 / 4 5 6 / _ 7 8`
- 目标：`3 2 1 / 6 4 5 / 8 7 _`（非标准八数码）
- 起始仅 **2、7** 为绿色

默认 `--puzzle 6` 为原 Lab 起始盘。