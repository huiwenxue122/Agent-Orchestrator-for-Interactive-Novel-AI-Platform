# Story Flow Orchestrator — LangGraph 设计说明

基于 `README_E.md` 的架构，将 **Story Flow Orchestrator** 用 LangGraph 实现为有状态图工作流，并利用 **Checkpoint** 与 **Human-in-the-Loop** 支持 IF-Line 回溯与用户选线。

---

## 0. 图结构 v3（当前实现）

### 0.1 逻辑关系总览

| 关系 | 含义 |
|------|------|
| **主生成链** | `parse` → `prompt_reinforcement` → `context_rag` → **`assemble_prompt`** → `llm_generate` → `context_verify` |
| **通过后** | `ok` → `output` → **`post_output_tasks`**（`kg_update` → `hint_recommendation` → `user_management`）→ `wait_for_user` |
| **可恢复失败** | `verify_status=retry` → **`retry_guard`** → 未超 `max_retries` 则回 `context_rag`；否则 → **`ask_clarification`** |
| **不可恢复失败** | `verify_status=fail` → **`ask_clarification`** → `wait_for_user` |
| **语义** | `assembled_context` = 检索材料；`assembled_prompt` = 给 LLM 的最终 system/user（便于 LangSmith 审计） |

### 0.2 主图（Mermaid）

```mermaid
flowchart TD
    START([START]) --> parse[parse_instruction]
    parse --> pr[prompt_reinforcement]
    pr --> rag[context_rag]
    rag --> ap[assemble_prompt]
    ap --> llm[llm_generate]
    llm --> verify[context_verify]
    verify -->|ok| out[output]
    verify -->|retry| rg[retry_guard]
    verify -->|fail| ask[ask_clarification]
    rg -->|retry_allowed| rag
    rg -->|retry_exhausted| ask
    out --> pot[post_output_tasks]
    pot --> wait[wait_for_user]
    ask --> wait
    wait --> parse

    subgraph KG["Knowledge Graph"]
        rag -.->|read| KG
        pot -.->|write inside kg_update| KG
    end
```

### 0.3 ASCII（与代码节点名一致）

```
  START → parse_instruction → prompt_reinforcement → context_rag
              ↑                                              │
              │         assemble_prompt → llm_generate → context_verify
              │              ↑              │                │
              │              │              │    ok ──► output ──► post_output_tasks ──► wait_for_user
              │              │              │    retry ──► retry_guard ──┬─► context_rag
              │              │              │    fail ──► ask_clarification ┘ exhausted
              │              │              │                              └──► ask_clarification
              └──────────────┴────────────── wait_for_user (interrupt) ────────┘
```

### 0.4 与「双起点」图的对应方式

- **架构图**：`START → hint_recommendation → user_management` 强调「Hint 与用户画像」是独立子系统。
- **编排图（本仓库）**：同一回合内顺序执行，避免 Hint 早于正文；**双起点** 通过以下方式落地而不矛盾：
  - **方案 A（推荐）**：会话创建时单独调用「用户管理 / 画像预取」API，结果写入 Redis/DB，主图 `prompt_reinforcement` 只读配置。
  - **方案 B**：LangGraph 用 `START` 后 **fan-out** 两个节点，在 `prompt_reinforcement` 前 **fan-in** 合并 state（实现成本高，适合强并行需求）。

### 0.5 节点与外部服务

| 节点 | 职责 |
|------|------|
| `parse_instruction` | Session 校验；重置 `retry_count`、`verify_*`、`assembled_prompt` 等 |
| `prompt_reinforcement` | 用户意图 + 风格 → `reinforced_prompt` |
| `context_rag` | 检索 + **KG 读** → `assembled_context` |
| `assemble_prompt` | 合并 reinforced + 玩家原文优先 + 上下文 + 重试修正 → `assembled_prompt` |
| `llm_generate` | 只读 `assembled_prompt` 调模型 → `generated_text` |
| `context_verify` | 设置 `verify_status`：`ok` / `retry` / `fail` |
| `retry_guard` | `retry_count` 与 `max_retries`；允许则回 `context_rag` |
| `ask_clarification` | `clarification_question` + `final_segment_text`；跳过 post-output side effects |
| `output` | `verify ok` 时定稿 `final_segment_text` |
| `post_output_tasks` | **副作用链**：`kg_update` → `hint_recommendation` → `user_management` |
| `wait_for_user` | `interrupt_after`；resume → `parse_instruction` |

---

## 1. 设计评价（新结构怎么样）

**优点**

1. **职责清晰**：把「Prompt 强化」「RAG+KG 读」「生成」「校验」「落库/输出」「KG 写」「Hint」「用户侧」拆开，比单一大 `post_process` 更易测试和观测。
2. **校验闭环**：`context_verify` 不通过回到 `context_rag` → `llm`，符合「检索/上下文错了就重拉再生成」的迭代方式，利于一致性修复（可附带 `verify_feedback` 进 state 指导下一轮 RAG）。
3. **KG 显式化**：读在检索与 Hint，写在段落定稿后，避免生成中途污染图数据，也便于审计「本段对应哪次 KG 更新」。

**风险与注意**

1. **重试成本**：回路会重复调用 LLM，需 **硬上限**（如 `MAX_RAG_RETRIES`）、超时与降级（超过次数则强制 `output` 并打标「未过审」）。
2. **双起点语义**：若真用并行子图，要定义好 **join 条件** 与失败一半成功一半时的处理；多数产品用 **会话级预取 + 主图顺序** 更简单。
3. **`prompt_reinforcement` 是否在重试时跳过**：当前实现重试从 `context_rag` 进入，不重复 `prompt_reinforcement`；若希望重试时改写 system prompt，可把边改为 `verify → prompt_reinforcement` 或把反馈并入 `context_rag`。

**总体**：新结构比线性 6 步更适合「长叙事一致性」和「可观测的 RAG+校验」；实现上优先保证 **顺序主链 + KG 读写边界 + 有界重试**，并行 Hint 线用会话 API 或后续子图扩展即可。

---

## 2. LangGraph：Checkpoint 与 Human-in-the-Loop

| 能力 | 用途 |
|------|------|
| **Checkpoint** | 每 super-step 持久化；`thread_id` 对应 session；`checkpoint_id` 支持回溯分支。 |
| **Human-in-the-Loop** | `interrupt_after=["wait_for_user"]`；前端展示 `final_segment_text` + `hints`；`Command(resume={...})` 写入 `user_choice` / `user_input_text` 后继续。 |

---

## 3. 状态 Schema（State）

```python
class OrchestratorState(TypedDict, total=False):
    session_id: str
    current_node_id: str
    parent_node_id: Optional[str]
    user_choice: Optional[str]
    user_input_text: Optional[str]
    style_tags: Optional[list[str]]
    story_world_summary: Optional[str]
    recent_story_summary: Optional[str]
    recent_dialogue: Optional[list[str]]

    reinforced_prompt: Optional[dict]
    assembled_context: Optional[dict]
    assembled_prompt: Optional[dict]  # system / user / meta
    generated_text: Optional[str]
    post_processed_text: Optional[str]
    verify_ok: Optional[bool]
    verify_status: Optional[str]
    verify_feedback: Optional[str]
    retry_count: Optional[int]
    max_retries: Optional[int]
    rag_retry_count: Optional[int]  # 与 retry_count 同步，兼容旧读者
    clarification_question: Optional[str]
    side_effects_status: Optional[str]
    final_segment_text: Optional[str]

    kg_snapshot_id: Optional[str]
    emotion_tone: Optional[str]
    hints: Optional[list[dict]]
    is_initial_turn: bool
```

---

## 4. 代码目录（当前）

```
backend/app/services/orchestrator/
├── constants.py      # VERIFY_ROUTE_*、RETRY_GUARD_*、DEFAULT_MAX_RETRIES
├── deps.py           # OrchestratorDeps、VerifyResult(outcome)
├── state.py
├── graph.py
└── nodes/
    ├── parse.py
    ├── prompt_reinforcement.py
    ├── context_rag.py
    ├── assemble_prompt.py
    ├── llm.py
    ├── context_verify.py
    ├── retry_guard.py
    ├── ask_clarification.py
    ├── output.py
    ├── post_output_tasks.py
    ├── kg_update.py
    ├── hint_recommendation.py
    ├── user_management.py
    └── wait_for_user.py
```

依赖注入：调用 `invoke_new_turn(..., deps=my_deps)` 或在 `config["configurable"]["orchestrator_deps"]` 传入 `OrchestratorDeps`；未传则使用进程内单例默认实现（内存 KG、可选 OpenAI）。

---

## 5. FastAPI 调用示例

```python
from app.services.orchestrator import (
    invoke_new_turn,
    resume_with_choice,
    get_state,
    default_orchestrator_deps,
)

deps = default_orchestrator_deps()  # 或自建 OrchestratorDeps 接入 Neo4j / 向量库等

invoke_new_turn(
    "if-line-123",
    {
        "session_id": "if-line-123",
        "current_node_id": "root",
        "is_initial_turn": True,
        "story_world_summary": "Optional world premise for RAG context.",
    },
    deps=deps,
    # llm_stream_callback=lambda t: push_sse(t),
)
# 中断于 wait_for_user；state 含 final_segment_text、hints

resume_with_choice("if-line-123", user_choice="B", deps=deps)

# 回溯
get_state("if-line-123", checkpoint_id="...")
```

---

## 6. Neo4j Aura、OpenAI 与「看到图结构」

### 6.1 先分清两种「图」

| 概念 | 是什么 | 接上 Neo4j / OpenAI 后 |
|------|--------|-------------------------|
| **LangGraph 编排图** | 代码里 `StateGraph` 的节点与边（parse → RAG → LLM → verify …） | **不会**因为接了 Neo4j 或 OpenAI 自动弹出界面；结构在编译后的图对象里，需导出或靠追踪工具看**执行路径**。 |
| **Neo4j Aura 里的图** | 小说世界知识图谱（人物、关系、伏笔等） | 在 **Neo4j Browser / Bloom** 里看数据图；这是**业务数据**，不是编排拓扑。 |

因此：**只配好 Neo4j Aura + OpenAI API，默认看不到 LangGraph 的结构图**；要「看编排结构」用下面两种方式之一。

### 6.2 静态看编排拓扑（推荐，零账号）

从本仓库导出 **Mermaid**，贴到 [mermaid.live](https://mermaid.live) 即可渲染：

```bash
# 在仓库根目录
PYTHONPATH=backend python backend/scripts/print_orchestrator_mermaid.py

# 或写入文件
PYTHONPATH=backend python backend/scripts/print_orchestrator_mermaid.py --out orchestrator_graph.mmd
```

代码等价于：`story_flow_graph.get_graph().draw_mermaid()`。

### 6.3 运行时看每一步（可以用 LangSmith）

**LangSmith** 适合看**某次 invoke 里实际跑了哪些节点**、耗时与嵌套调用，而不是替代上面的静态拓扑图。

1. 安装（若尚未）：`pip install langsmith`（`langgraph` 场景下常用）。
2. 环境变量（官方文档：[Trace LangGraph applications](https://docs.langchain.com/langsmith/trace-with-langgraph)）：

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=你的_LangSmith_API_Key
export OPENAI_API_KEY=你的_OpenAI_Key   # 若要走真实 LLM
# 可选：export LANGSMITH_PROJECT=你的项目名
```

3. 像平常一样 `invoke_new_turn(...)`；打开 [smith.langchain.com](https://smith.langchain.com) 对应 Project，查看 **Trace** 的 **Details** 视图，可看到图节点级别的执行顺序。

**本仓库一键跑通 LangSmith 第 4 步（替代码里的 weather agent 示例）**：在仓库根目录执行  
`PYTHONPATH=backend python backend/scripts/run_orchestrator_langsmith.py`  
（需已配置 `.env` 中的 `LANGSMITH_*`；脚本会加载项目根目录的 `.env`。）

**LangGraph Studio（`langgraph dev`）**：根目录已有 `langgraph.json` + `langgraph_entry.py`。`langgraph_entry` 使用 **无自定义 checkpointer** 的图（`build_story_flow_graph(for_langgraph_api=True)`），否则 LangGraph API 会报 `GraphLoadError`（平台自行管理持久化）。本地脚本 `invoke_new_turn` 仍使用带内存 checkpointer 的默认图。  
先在本机终端运行 `langgraph dev` 并保持运行，再在浏览器打开终端里打印的 Studio URL；若出现 `Failed to fetch`，多半是 **本机 API 未启动** 或 **端口被占用**（默认 `2024`）。

**说明**：当前编排里 LLM 走的是原生 `openai` SDK（`deps.OpenAIStoryLLM`），LangSmith 对 LangGraph 顶层 trace 仍会记录；若你希望 **每次 chat completion 都细粒度进 LangSmith**，可对 `generate_segment` 使用 LangSmith 的 `@traceable` 或 `wrap_openai`（见同一文档 *Without LangChain* 小节）。

### 6.4 Neo4j Aura 在本项目里要做什么

在 `OrchestratorDeps` 里把默认的 `InMemoryKnowledgeGraph` 换成你自己的实现（`KnowledgeGraphService` 协议）：`query_for_rag` / `apply_segment` 内用 **Neo4j Python Driver** 连 Aura（`NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`）。接好后：**剧情与 Hint 会用到真实图数据**，但 **仍不会**自动展示 LangGraph 结构——结构仍用 6.2 / 6.3。

---

## 7. 历史版本（参考）

- **v1**：`context_assembly` → `post_process` → `update_state` → `hint_generation` …  
- **v2**：加入 `prompt_reinforcement`、`context_rag`、`context_verify` 直连重试、`kg_update` 链式 Hint。  
- **v3（当前）**：`assemble_prompt`、`retry_guard`、`ask_clarification`、`post_output_tasks`，`VerifyResult.outcome` 三分支路由。
