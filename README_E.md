# 殊途 (Shutu) — Interactive Novel AI Platform

> **"殊途同归"** — All roads lead to Rome. Everyone can write their own story line.

An AI-powered content platform that enables anyone to easily rewrite and continue novels. Through a **Context Memory Engine** for narrative coherence and an **Intelligent Hint Recommendation Algorithm** to lower the creative barrier, we deliver an immersive "IF-Line" interactive storytelling experience.

---

## 🏗️ System Architecture Overview

```
                          ┌─────────────────────────────────────────┐
                          │   Frontend — Immersive Reading/Creation   │
                          │  ┌───────────┐ ┌──────────┐ ┌─────────┐  │
                          │  │ Story     │ │ Hint Card│ │ IF-Line │  │
                          │  │ Reader    │ │ Selector │ │ Timeline│  │
                          │  └───────────┘ └──────────┘ └─────────┘  │
                          └────────────────┬────────────────────────┘
                                           │ WebSocket / SSE (Real-time Push)
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     API Gateway / Backend (Python + FastAPI)                  │
│                                                                              │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐  ┌───────────┐   │
│  │ Auth &       │  │ Session &      │  │ Story Flow       │  │ SSE/WS    │   │
│  │ User Service │  │ IF-Line Manager│  │ Orchestrator     │  │ Push      │   │
│  └──────────────┘  └────────────────┘  └──────────────────┘  └───────────┘   │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
┌──────────────────┐ ┌────────────────┐ ┌─────────────────────┐
│  AI Engine Core  │ │ Context Memory │ │  Hint Recommender   │
│                  │ │    Engine      │ │     Engine          │
│ ┌──────────────┐ │ │ ┌────────────┐ │ │ ┌─────────────────┐ │
│ │ LLM Adapter  │ │ │ │ Sliding    │ │ │ │ Narrative-Aware  │ │
│ │ (Multi-Model)│ │ │ │ Window +   │ │ │ │ Hint Generator   │ │
│ └──────────────┘ │ │ │ Summary    │ │ │ └─────────────────┘ │
│ ┌──────────────┐ │ │ │ Manager    │ │ │ ┌─────────────────┐ │
│ │ Prompt       │ │ │ └────────────┘ │ │ │ User Preference  │ │
│ │ Template     │ │ │ ┌────────────┐ │ │ │ Learner          │ │
│ │ Engine       │ │ │ │ KG-based   │ │ │ └─────────────────┘ │
│ └──────────────┘ │ │ │ RAG Module │ │ │ ┌─────────────────┐ │
│ ┌──────────────┐ │ │ └────────────┘ │ │ │ Diversity &     │ │
│ │ Safety &     │ │ │ ┌────────────┐ │ │ │ Surprise        │ │
│ │ Style Filter │ │ │ │ Emotion &  │ │ │ │ Balancer        │ │
│ └──────────────┘ │ │ │ Tone State │ │ │ └─────────────────┘ │
└──────────────────┘ │ │ Tracker    │ │ └─────────────────────┘
                     │ └────────────┘ │
                     └────────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
┌──────────────────┐ ┌────────────────┐ ┌─────────────────────┐
│   PostgreSQL     │ │  Neo4j / Graph │ │ Redis               │
│   (Users, Story  │ │  (Knowledge   │ │ (Session Cache,     │
│    Metadata)     │ │   Graph)      │ │  Real-time State)   │
│                  │ │               │ │                     │
└──────────────────┘ └────────────────┘ └─────────────────────┘
                               │
                               ▼
                     ┌─────────────────┐
                     │  Vector Store   │
                     │  (Pinecone /    │
                     │   Milvus)       │
                     │  Embeddings for │
                     │  Semantic RAG   │
                     └─────────────────┘
```

---

## 🧠 Core Modules Deep Dive

### 1. Frontend — Immersive Interaction Layer

| Component | Responsibility |
|-----------|----------------|
| **Story Reader** | Immersive story reader with streaming typewriter effect and chapter pagination |
| **Hint Card Selector** | After story generation, smoothly displays 3 AI-generated action options (A/B/C) + custom input field at the bottom |
| **IF-Line Timeline** | Visual branch tree; users can backtrack to any node to re-select and create new branches |

**Tech Stack**: React / Next.js + Framer Motion (animations) + WebSocket (real-time push)

---

### 2. Backend — API & Flow Orchestration (Python + FastAPI)

#### 2.1 Auth & User Service
- User registration/login (OAuth2 / JWT)
- User profile storage (reading preferences, creative style tags)

#### 2.2 Session & IF-Line Manager ⭐ Moat Component
- Creates independent `session_id` for each user's each "IF-Line"
- IF-Line data structure — tree-based branch management:

```
IF-Line Tree Data Structure:

        [root: "Original Novel Opening"]
              │
        [node_1: "Protagonist Enters Forest"]
             ╱           ╲
  [node_2a: "Draw Sword"]   [node_2b: "Hold Back"]
       │                            │
  [node_3a: ...]               [node_3b: ...]
```

- Each node stores: `{node_id, parent_id, user_choice, generated_text, kg_snapshot_id, timestamp}`
- Supports **Backtrack**: users can return to any historical node to re-select

#### 2.3 Story Flow Orchestrator
Core orchestration engine handling a complete "User → AI → User" cycle:

```
User Selection/Input
      │
      ▼
┌─────────────────┐
│ 1. Parse User   │
│    Instruction  │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. Context      │──→ Assemble context from KG + Vector DB + Sliding Window Summary
│    Assembly     │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. LLM Generate │──→ Stream story generation (SSE push to frontend)
│    Story Segment│
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. Post-Process │──→ Safety filter / Style consistency check / Logic coherence validation
└────────┬────────┘
         ▼
┌─────────────────┐
│ 5. Update State │──→ Update KG (new characters/relations) + Context State + IF-Line Tree
└────────┬────────┘
         ▼
┌─────────────────┐
│ 6. Hint         │──→ Call Hint Recommender to generate next set of options
│    Generation   │
└────────┬────────┘
         ▼
  Push {new_story, hints[]} to Frontend
```

---

### 3. AI Engine Core — LLM Adapter Layer

| Component | Responsibility |
|-----------|----------------|
| **LLM Adapter (Multi-Model)** | Unified interface for GPT-4o / Claude / DeepSeek / local models; supports fallback and load balancing |
| **Prompt Template Engine** | Dynamic prompt assembly — inject character settings, world-building, previous story summaries, KG relations, user style preferences |
| **Safety & Style Filter** | Content safety review + style consistency (prevents sudden tone shifts) |

---

### 4. Context Memory Engine ⭐ Core Moat

> **Goal**: Solve the limited LLM context window problem in long-form narratives, ensuring Chapter 100 still remembers foreshadowing from Chapter 1.

#### 4.1 Sliding Window + Hierarchical Summary Manager
```
Context Assembly Strategy:

┌──────────────────────────────────────────────────────────────┐
│                    LLM Prompt Context Budget                 │
│                                                              │
│  ┌──────────────┐  ┌────────────┐  ┌───────────────────────┐ │
│  │ Global       │  │ Recent     │  │ Current IF-Line       │ │
│  │ Summary      │  │ Chapter    │  │ Last N Rounds         │ │
│  │ (Core info   │  │ Summary    │  │ Full Dialogue         │ │
│  │  of novel)   │  │ (Last 5 ch)│  │ (Last 3-5 rounds)     │ │
│  │ ~500 tokens  │  │ ~1000 tok  │  │ ~2000 tokens          │ │
│  └──────────────┘  └────────────┘  └───────────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ KG Retrieval Results (characters/relations/items/foreshadowing) │
│  │ ~1000 tokens                                              │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

- **Three-tier Summary System**: Global Summary → Chapter Summary → Paragraph Summary; dynamically allocates tokens based on context budget
- **Incremental Update**: After each new story generation, only update affected summary levels

#### 4.2 Knowledge Graph (KG) + RAG Module ⭐
```
Knowledge Graph Schema:

  [Character: Lin Feng] ──Master-Student──→ [Character: Elder Zhang]
       │                                          │
    Owns Item                              Enemy Relation
       │                                          │
       ▼                                          ▼
  [Item: Xuantie Sword]                   [Character: Demon Sect Leader]
       │
    Appears in Scene
       │
       ▼
  [Location: Tianshan Sect]──Located in──→ [Location: Western Region]
       │
    Event Occurs
       │
       ▼
  [Event: Martial Arts Conference] ──Involves──→ [Foreshadowing: Mysterious Letter]
```

- **Dynamic Update**: After each story generation, automatically extract new entities/relations and inject into KG
- **RAG Retrieval**: Query KG before generation to fetch character relations, unresolved foreshadowing, item locations relevant to current scene
- **Consistency Check**: After generation, verify against KG for contradictions (e.g., dead character revival, item location conflicts)

#### 4.3 Emotion & Tone State Tracker 🆕
- Tracks narrative **emotional curve** (tension → relief → climax)
- Ensures AI-generated content matches current narrative rhythm
- Influences Hint recommendation (no mundane options during tense moments)

---

### 5. Hint Recommender Engine ⭐ Core Moat

> **Goal**: Generate high-quality options that make users "want to click every one," not boring A/B/C choices.

#### 5.1 Narrative-Aware Hint Generator
```
Hint Generation Pipeline:

  Current Story Context
       │
       ▼
┌─────────────────────────────────────────────┐
│         Hint Candidate Generation           │
│                                             │
│  Generate candidate Hints from multiple dims:│
│  ├─ 📖 Plot-Advancing: Drive main storyline │
│  ├─ 👤 Character Interaction: Dialogue/conflict with a character │
│  ├─ 🔍 Exploration: Explore environment/reveal secrets │
│  ├─ ⚡ Plot Twist: Introduce new conflict/reversal │
│  └─ ❤️ Emotional Expression: Relationship development/inner monologue │
└────────────┬────────────────────────────────┘
             ▼
┌─────────────────────────────────────────────┐
│          Hint Ranking & Selection           │
│                                             │
│  Ranking Factors:                           │
│  ├─ Narrative Tension Score                 │
│  ├─ User Preference Match Score             │
│  ├─ Diversity Score                         │
│  └─ Foreshadowing Relevance                 │
└────────────┬────────────────────────────────┘
             ▼
      Final Output: 3 Hints
  (Ensure coverage of different types + at least 1 high-tension option)
```

#### 5.2 User Preference Learner 🆕
- Records user's historical choice patterns (prefer combat? mystery? romance?)
- Builds **user creative profile** for personalized recommendations
- Retains **surprise factor** — occasionally recommend directions user has never tried

#### 5.3 Diversity & Surprise Balancer 🆕
- Ensures **sufficient differentiation** among 3 options (no 3 "fight" options)
- **Exploration vs. Exploitation**: 70% match user preference / 30% explore new directions
- Prevents narrative from falling into repetitive patterns

---

## 🗄️ Data Storage Architecture

| Storage | Purpose | Tech Stack |
|---------|---------|------------|
| **Relational DB** | User info, Story metadata, IF-Line tree structure | PostgreSQL |
| **Graph DB** | Knowledge Graph (characters/relations/events/foreshadowing) | Neo4j |
| **Vector DB** | Semantic retrieval — story segment embeddings, similar scene lookup | Milvus / Pinecone |
| **Cache** | Active session state, real-time context, hot data | Redis |
| **Object Storage** | Raw novel text, user export content | MinIO / S3 |

---

## 🔄 Core Data Flow — One Complete Interaction

```
   ┌─────────┐
   │  User   │ ──Select Hint B: "Hold Back"──→ Frontend
   └─────────┘                              │
                                            ▼
                                     ┌──────────────┐
                                     │  API Gateway  │
                                     │  (FastAPI)    │
                                     └──────┬───────┘
                                            │
                              ┌─────────────┼──────────────────┐
                              ▼             ▼                  ▼
                      ┌──────────┐  ┌──────────────┐  ┌──────────────┐
                      │ Session  │  │   Context     │  │     KG       │
                      │ Manager  │  │   Assembly    │  │    Query     │
                      │          │  │               │  │              │
                      │ Validate │  │   Assemble:   │  │  Query:      │
                      │ session  │  │ - Global sum  │  │ - Current    │
                      │ Update IF│  │ - Recent sum  │  │   characters │
                      │ Tree     │  │ - Recent conv │  │ - Relations  │
                      └──────────┘  └──────┬───────┘  └──────┬───────┘
                                           │                  │
                                           └────────┬─────────┘
                                                    ▼
                                           ┌────────────────┐
                                           │   LLM Generate  │
                                           │   (Streaming)   │
                                           │                 │
                                           │  System Prompt: │
                                           │  You are a novelist... │
                                           │  + Global summary      │
                                           │  + KG relations        │
                                           │  + Recent story        │
                                           │  + User choice         │
                                           └────────┬────────┘
                                                    │
                                    ┌───────────────┼───────────────┐
                                    ▼               ▼               ▼
                            ┌──────────┐   ┌──────────────┐  ┌──────────┐
                            │Consistency│   │  KG Update    │  │ Hint     │
                            │& Safety   │   │ (Extract new  │  │ Generate │
                            │Filter     │   │  entities &   │  │ 3 options│
                            │           │   │  relations)   │  │          │
                            └──────────┘   └──────────────┘  └──────────┘
                                    │               │               │
                                    └───────────────┼───────────────┘
                                                    ▼
                                           ┌────────────────┐
                                           │  SSE Push to    │
                                           │  Frontend       │
                                           │                 │
                                           │  {story, hints} │
                                           └────────────────┘
```

---

## 🚀 MVP Phased Plan

### Phase 1 — Core Loop (MVP)
- [ ] FastAPI base framework + Session management
- [ ] Basic Prompt Template + LLM Adapter (OpenAI first)
- [ ] Simple sliding window context (last N rounds)
- [ ] Basic Hint generation (LLM directly generates 3 options)
- [ ] Minimal frontend (Story Reader + Hint Card)

### Phase 2 — Memory Enhancement
- [ ] Integrate Neo4j, implement Knowledge Graph auto-construction
- [ ] Implement three-tier summary system
- [ ] KG-based RAG retrieval
- [ ] Consistency check module

### Phase 3 — Recommendation Evolution
- [ ] Hint multi-dimensional candidate generation
- [ ] User preference learning system
- [ ] Diversity & Surprise Balancer
- [ ] Emotion & Tone Tracker

### Phase 4 — Scale
- [ ] Multi-Model support + load balancing
- [ ] IF-Line branch visualization Timeline
- [ ] Community features — share/fork others' IF-Lines
- [ ] Multi-language support

---

## 🛡️ Moat Analysis

| Moat | Details |
|------|---------|
| **Context Memory Coherence** | Three-tier summary + KG + RAG combined strategy ensures long-form narratives don't lose critical info. Competitors typically only do simple truncation. |
| **Hint Recommendation Algorithm** | Recommendation system based on narrative tension, user preference, and diversity — not simple LLM generation. |
| **Consistency Check** | KG-driven automatic contradiction detection — critical for interactive branch narratives. |
| **User Preference Flywheel** | The more users engage, the better we understand them — more accurate recommendations → higher satisfaction → more data → even better recommendations. |

---

## 📂 Project Directory Structure (Planned)

```
殊途/
├── frontend/                  # Frontend application
│   ├── src/
│   │   ├── components/        # UI components (StoryReader, HintCard, Timeline)
│   │   ├── hooks/             # WebSocket / SSE hooks
│   │   ├── stores/            # State management
│   │   └── styles/            # Styles
│   └── package.json
│
├── backend/                   # Python + FastAPI
│   ├── app/
│   │   ├── api/               # API routes
│   │   ├── core/              # Config, security
│   │   ├── models/            # Data models
│   │   ├── services/
│   │   │   ├── session/       # Session & IF-Line Manager
│   │   │   ├── orchestrator/  # Story Flow Orchestrator
│   │   │   ├── ai_engine/     # LLM Adapter, Prompt Engine
│   │   │   ├── context/       # Context Memory Engine
│   │   │   ├── kg/            # Knowledge Graph management
│   │   │   └── hint/          # Hint Recommender Engine
│   │   └── db/                # DB connection & migrations
│   ├── tests/
│   └── pyproject.toml
│
├── infra/                     # Infrastructure & Deployment
│   ├── docker-compose.yml     # Local dev environment
│   └── k8s/                   # K8s deployment config
│
└── README.md
```

---

## 🔧 Tech Stack Summary

| Layer | Technology |
|-------|------------|
| **Frontend** | React / Next.js, Framer Motion, WebSocket |
| **Backend** | Python 3.12+, FastAPI, Pydantic, Celery (async tasks) |
| **AI Engine** | **LangGraph** (stateful graph workflow + Checkpoint + Human-in-the-Loop), LlamaIndex (RAG), OpenAI / Claude API |
| **Graph DB** | Neo4j (KG storage & query) |
| **Vector DB** | Milvus / Pinecone (semantic retrieval) |
| **Relational DB** | PostgreSQL (users & metadata) |
| **Cache** | Redis (Session + real-time state) |
| **Deployment** | Docker + Kubernetes |
| **Monitoring** | Prometheus + Grafana, LLM call logging |
