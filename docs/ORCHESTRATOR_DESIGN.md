# Story Flow Orchestrator — LangGraph 设计说明

基于 `README_E.md` 的架构，将 **Story Flow Orchestrator** 用 LangGraph 实现为有状态图工作流，并利用 **Checkpoint** 与 **Human-in-the-Loop** 支持 IF-Line 回溯与用户选线。

---

## 1. 文档中的流水线（与节点映射）

README 中的一轮「User → AI → User」流程：

| 步骤 | README 描述 | LangGraph 节点 |
|------|-------------|----------------|
| 1 | Parse User Instruction | `parse_instruction` |
| 2 | Context Assembly（KG + Vector + Sliding Window） | `context_assembly` |
| 3 | LLM Generate Story（流式 SSE） | `llm_generate` |
| 4 | Post-Process（安全 / 风格 / 一致性） | `post_process` |
| 5 | Update State（KG + Context + IF-Line Tree） | `update_state` |
| 6 | Hint Generation（3 个选项） | `hint_generation` |
| — | **等待用户选择** | `wait_for_user`（interrupt） |
| 下一轮 | 用户选择 A/B/C 或自定义 | 从 `parse_instruction` 继续 |

---

## 2. LangGraph 的三种用法

| 能力 | 用途 |
|------|------|
| **Stateful graph workflow** | 6 步 + 等待用户 组成有向图，状态在节点间传递。 |
| **Checkpoint** | 每步持久化状态；回溯时用 `checkpoint_id` 恢复到历史节点，实现 IF-Line「回到某节点重选」。 |
| **Human-in-the-Loop** | 在 `hint_generation` 之后 `interrupt_after`，前端展示 3 个 Hint；用户选完后用 `Command(resume=...)` 恢复，继续执行 `parse_instruction` 开始下一轮。 |

---

## 3. 图结构（环路 + 中断）

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                                                         │
  START ──────────► parse_instruction ──► context_assembly ──► llm_generate   │
       (首轮输入)         ▲                    │                      │         │
                         │                    ▼                      ▼         │
                         │             post_process ──► update_state ──► hint_generation
                         │                    │                      │         │
                         │                    │                      ▼         │
                         └────────────────── wait_for_user ◄──────────────────┘
                                    (interrupt_after)
                                    resume = 用户选择 → 回到 parse_instruction
```

- **首轮**：`invoke(initial_input, config)`，从 `parse_instruction` 进入，最后在 `wait_for_user` 后中断。
- **后续轮**：用户选完后 `invoke(Command(resume={...}), config)`，从 `wait_for_user` 的下一节点（即 `parse_instruction`）继续，形成环路。

---

## 4. 状态 Schema（State）

与 README 的 IF-Line 节点字段和上下文预算对齐：

```python
class OrchestratorState(TypedDict):
    # Session & IF-Line
    session_id: str
    current_node_id: str           # IF-Line 当前节点
    parent_node_id: Optional[str]  # 回溯/分支用
    user_choice: Optional[str]     # 用户选的 Hint 或自定义文本（resume 写入）
    user_input_text: Optional[str] # 自定义输入

    # Context Assembly 输出
    assembled_context: Optional[dict]  # { global_summary, recent_summary, kg_relations, ... }

    # LLM 输出与后处理
    generated_text: Optional[str]      # 本段剧情
    post_processed_text: Optional[str] # 过滤/一致性后

    # Update State 输出
    kg_snapshot_id: Optional[str]      # 本步后的 KG 快照
    emotion_tone: Optional[str]        # 情绪/节奏（给 Hint 用）

    # Hint 输出（推给前端）
    hints: Optional[list[dict]]        # 3 个 { id, text, type?, ... }

    # 首轮 vs 后续轮
    is_initial_turn: bool
```

- **Checkpoint**：每步后自动持久化该 state，便于回溯。
- **Backtrack**：从历史 `checkpoint_id` 用 `get_state(config)` 取回 state，再用 `invoke(..., config={"checkpoint_id": "..."})` 从该 checkpoint 继续，实现「回到某节点重选」。

---

## 5. Human-in-the-Loop 与 Resume

- **interrupt_after**：在 `wait_for_user` 后中断（或直接在 `hint_generation` 后中断，视是否要单独 `wait_for_user` 节点而定）。中断时前端拿到 `state["hints"]` 和 `state["generated_text"]`，展示剧情 + 3 个选项。
- **Resume**：用户选择后，后端调用：
  - `graph.invoke(Command(resume={"user_choice": "B", "user_input_text": "..."}), config)`
  - 状态合并 `user_choice` / `user_input_text` 后，从下一节点（`parse_instruction`）继续，开始新一段剧情生成。

---

## 6. 与其它模块的对接

| 节点 | 依赖服务（在代码中注入或通过 state/config 传） |
|------|-----------------------------------------------|
| parse_instruction | Session/IF-Line Manager（校验 session、取当前节点） |
| context_assembly | Context Memory Engine（Sliding Window + Summary）、KG 查询、Vector RAG |
| llm_generate | AI Engine（LLM Adapter + Prompt Template），流式输出用 callback 推 SSE |
| post_process | AI Engine（Safety & Style Filter）、KG 一致性检查 |
| update_state | Session Manager（写 IF-Line 树）、KG Update、Context State 增量更新 |
| hint_generation | Hint Recommender Engine（候选生成 + 排序 + 3 选） |

---

## 7. 代码目录建议（与 README 一致）

```
backend/app/services/orchestrator/
├── __init__.py
├── state.py          # OrchestratorState 定义
├── nodes/
│   ├── __init__.py
│   ├── parse.py
│   ├── context.py
│   ├── llm.py
│   ├── post_process.py
│   ├── update_state.py
│   ├── hint.py
│   └── wait_for_user.py
├── graph.py          # 建图、compile(checkpointer=...)、interrupt_after
└── dependencies.py  # 注入 Session/KG/LLM/Hint 等依赖（可选）
```

---

## 8. 回溯（Backtrack）在 API 层的用法

- 前端在 IF-Line Timeline 上选「回到节点 N」。
- 后端根据 N 查到对应 `checkpoint_id`（需在 IF-Line 节点表或 checkpoint 元数据里存 `node_id <-> checkpoint_id` 映射）。
- 调用 `graph.invoke(Command(resume={"user_choice": "新选择"}), config={"configurable": {"thread_id": session_id, "checkpoint_id": target_checkpoint_id}})`，从该 checkpoint 之后继续，实现分支/重选。

以上即为基于 README 的 LangGraph Story Flow Orchestrator 设计与实现要点。

---

## 9. 代码里怎么用（FastAPI 示例）

```python
# 首轮：创建 session，传入 opening
from app.services.orchestrator import invoke_new_turn, resume_with_choice, get_state

result = invoke_new_turn(
    session_id="if-line-123",
    initial_input={
        "session_id": "if-line-123",
        "current_node_id": "root",
        "is_initial_turn": True,
    },
)
# result 会在 wait_for_user 后中断；result["hints"] 推给前端

# 用户选 B 后
resume_with_choice(session_id="if-line-123", user_choice="B")
# 或自定义输入
resume_with_choice(session_id="if-line-123", user_input_text="主角拔剑迎战")

# 回溯：从某 checkpoint 继续（需在业务层维护 node_id <-> checkpoint_id）
snapshot = get_state("if-line-123", checkpoint_id="xxx")
# 再用 graph.invoke(Command(resume={...}), config={"configurable": {"thread_id": "...", "checkpoint_id": "xxx"}})
```
