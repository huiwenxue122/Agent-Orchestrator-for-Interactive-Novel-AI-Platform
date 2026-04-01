# Story Flow Orchestrator — LangGraph 设计说明

基于 `README_E.md` 的架构，将 **Story Flow Orchestrator** 用 LangGraph 实现为有状态图工作流，并利用 **Checkpoint** 与 **Human-in-the-Loop** 支持 IF-Line 回溯与用户选线。

---

## 0. 图结构 v2（当前实现）

### 0.1 逻辑关系总览（含 Knowledge Graph）

你们讨论的新结构可以整理为三条「关系」+ 一条主执行链：

| 关系 | 含义 |
|------|------|
| **主链（生成）** | `START` → `prompt_reinforcement` → `context_rag` → `llm` → `context_verify` →（通过）→ `output` →（更新）→ **Knowledge Graph** |
| **校验失败回路** | `context_verify` →（不通过）→ `context_rag` → `llm` → `context_verify` … |
| **Hint / 用户** | `hint_recommendation` → `user_management`；Hint 侧依赖 **Knowledge Graph**（读） |
| **KG 读写** | `context_rag`、`hint_recommendation` **读 KG**；`output` 之后 **写 KG**（本仓库用独立节点 `kg_update` 表达「写」） |

> **说明**：图上的「同时 start → hint recommendation → user management」表示 **产品/架构上** Hint 与用户偏好是一条独立能力线；在 **单次剧情生成回合** 里，Hint 必须在「本段正文已产出」之后才有意义，因此 **运行时主图** 采用顺序：`output` → `kg_update` → `hint_recommendation` → `user_management` → `wait_for_user`。若将来要在会话初始化时预拉用户画像，可另建 **并行子图** 或独立 API，在 `START` 分叉后于 `prompt_reinforcement` 前做 **fan-in**（见 0.4）。

### 0.2 主图（Mermaid）

```mermaid
flowchart TD
    START([START]) --> parse[parse_instruction]
    parse --> pr[prompt_reinforcement]
    pr --> rag[context_rag]
    rag --> llm[llm_generate]
    llm --> verify[context_verify]
    verify -->|ok| out[output]
    verify -->|not ok| rag
    out --> kg[kg_update]
    kg --> hint[hint_recommendation]
    hint --> um[user_management]
    um --> wait[wait_for_user]
    wait --> parse

    subgraph KG["Knowledge Graph（跨节点读写）"]
        direction TB
        rag -.->|read| KG
        hint -.->|read| KG
        kg -.->|write| KG
    end
```

### 0.3 ASCII（与代码节点名一致）

```
  START
    │
    ▼
parse_instruction ──► prompt_reinforcement ──► context_rag ◄────┐
    ▲                      │ read KG (in rag)                    │
    │                      ▼                                     │ not ok
    │                 llm_generate                               │
    │                      ▼                                     │
    │                 context_verify ── ok ──► output              │
    │                      │                     │               │
    │                      │                     ▼               │
    │                      │                kg_update ── write KG  │
    │                      │                     │               │
    │                      │                     ▼               │
    │                      │         hint_recommendation ─ read KG│
    │                      │                     │               │
    │                      │                     ▼               │
    │                      │            user_management          │
    │                      │                     │               │
    │                      │                     ▼               │
    │                      └──── not ok ────────┘      wait_for_user
    │                              │                  (interrupt)
    └──────────────────────────────┴──────────────────────┘
```

### 0.4 与「双起点」图的对应方式

- **架构图**：`START → hint_recommendation → user_management` 强调「Hint 与用户画像」是独立子系统。
- **编排图（本仓库）**：同一回合内顺序执行，避免 Hint 早于正文；**双起点** 通过以下方式落地而不矛盾：
  - **方案 A（推荐）**：会话创建时单独调用「用户管理 / 画像预取」API，结果写入 Redis/DB，主图 `prompt_reinforcement` 只读配置。
  - **方案 B**：LangGraph 用 `START` 后 **fan-out** 两个节点，在 `prompt_reinforcement` 前 **fan-in** 合并 state（实现成本高，适合强并行需求）。

### 0.5 节点与外部服务

| 节点 | 职责 |
|------|------|
| `parse_instruction` | Session / IF-Line 校验；每轮重置 `rag_retry_count` |
| `prompt_reinforcement` | 用户意图 + 风格约束注入 Prompt |
| `context_rag` | 滑动窗口 + 向量检索 + **KG 查询**，组装上下文 |
| `llm_generate` | 流式生成正文 |
| `context_verify` | 安全 / 风格 / **逻辑与 KG 一致性**；失败则回到 `context_rag`（有次数上限） |
| `output` | 对外输出的最终段落字段（如 `final_segment_text`） |
| `kg_update` | 根据本段正文 **更新 KG**（实体/关系/快照） |
| `hint_recommendation` | 结合正文 + KG + 张力等生成 3 个 Hint |
| `user_management` | 记录选择偏好、探索/利用计数等 |
| `wait_for_user` | `interrupt_after`；resume 后继续 `parse_instruction` |

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
    generated_text: Optional[str]
    post_processed_text: Optional[str]
    verify_ok: Optional[bool]
    rag_retry_count: Optional[int]
    verify_feedback: Optional[str]
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
├── deps.py           # OrchestratorDeps + Protocol 与默认实现（Session / KG / LLM / Verify / Hint / User）
├── state.py
├── graph.py          # 建图、invoke / resume（可传 orchestrator_deps、llm_stream_callback）
└── nodes/
    ├── parse.py
    ├── prompt_reinforcement.py
    ├── context_rag.py
    ├── llm.py
    ├── context_verify.py
    ├── output.py
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

## 7. 旧版流水线（参考，已由 v2 替代）

原先线性结构为：`parse_instruction` → `context_assembly` → `llm_generate` → `post_process` → `update_state` → `hint_generation` → `wait_for_user`。v2 将其拆解为 **prompt_reinforcement**、**context_rag**、**context_verify 回路**、**output**、**kg_update**，并将 Hint 与用户管理显式串联在 KG 更新之后。
