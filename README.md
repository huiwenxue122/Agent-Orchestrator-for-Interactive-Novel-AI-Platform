# 殊途 (Shutu) — Interactive Novel AI Platform

> **「殊途同归」** — 人人可书写自己的故事线。

基于 AI 的互动小说平台：通过**上下文记忆引擎**保证叙事连贯，通过**智能 Hint 推荐**降低创作门槛，提供沉浸式 IF-Line 分支叙事体验。

- 完整架构与模块说明见 **[README_E.md](./README_E.md)**（英文）

---

## 当前进展

| 模块 | 状态 | 说明 |
|------|------|------|
| 架构文档 | ✅ | README_E.md：系统架构、数据流、Tech Stack、MVP 分阶段计划 |
| 依赖清单 | ✅ | `requirements.txt`（FastAPI、LangGraph、LlamaIndex、Neo4j、Redis 等） |
| Story Flow Orchestrator | 🚧 骨架完成 | 基于 **LangGraph** 的剧情编排图（Checkpoint + Human-in-the-Loop） |
| 编排器设计文档 | ✅ | [docs/ORCHESTRATOR_DESIGN.md](./docs/ORCHESTRATOR_DESIGN.md)：状态、节点、图结构、与 FastAPI 对接方式 |
| 前端 / API Gateway / Session / KG / Hint | ⏳ 待开发 | 按 README_E 分阶段推进 |

**已实现编排流水线（占位逻辑）：**

`parse_instruction` → `context_assembly` → `llm_generate` → `post_process` → `update_state` → `hint_generation` → `wait_for_user`（中断）→ 循环

- 使用 `interrupt_after` 在出 Hint 后等待用户选择，再通过 `Command(resume=...)` 继续下一轮。
- 使用 Checkpoint 支持按 `thread_id` / `checkpoint_id` 回溯到历史节点重选分支。

---

## 项目结构

```
├── README.md              # 本文件（项目简介 + 当前进展）
├── README_E.md            # 完整架构设计（英文）
├── requirements.txt      # Python 依赖
├── docs/
│   └── ORCHESTRATOR_DESIGN.md   # 编排器设计与实现说明
└── backend/
    └── app/
        └── services/
            └── orchestrator/   # LangGraph Story Flow 编排器
                ├── state.py    # 状态 schema
                ├── graph.py    # 建图、invoke/resume/get_state
                └── nodes/      # 各步骤节点（待接入真实服务）
```

---

## 本地运行

```bash
# 创建虚拟环境并安装依赖
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 在项目根目录验证编排器（需设置 PYTHONPATH）
PYTHONPATH=backend python -c "
from app.services.orchestrator import invoke_new_turn, resume_with_choice
r = invoke_new_turn('test-session', {'session_id': 'test-session', 'current_node_id': 'root', 'is_initial_turn': True})
print('Hints:', r.get('hints'))
"
```

---

## 后续计划（参考 README_E MVP）

1. **Phase 1**：FastAPI 入口、Session 管理、简单 Prompt + LLM 接入、基础 Hint 生成、简易前端。
2. **Phase 2**：Neo4j 知识图谱、三层摘要、KG RAG、一致性校验。
3. **Phase 3**：Hint 多维度候选、用户偏好学习、多样性/惊喜平衡、情绪节奏追踪。
4. **Phase 4**：多模型、IF-Line 时间线可视化、社区分享、多语言。

---

## License

See repository.
