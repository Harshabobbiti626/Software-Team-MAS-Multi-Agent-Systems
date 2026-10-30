# AI, ML & GENERATIVE AI STANDARDS PLAYBOOK
## Production Guidelines for LLM Orchestration, RAG, Agents & Evaluation

---

## 1. DETERMINISTIC LLM APPLICATION ARCHITECTURE
- **Structured Outputs Only**:
  Never rely on loose text or raw string parsing for programmatic control. Enforce structured schemas using native Function Calling or Pydantic/Zod response models.
- **Defensive Parser & Repair**:
  If the LLM generates a slightly invalid payload, pass it through an automated schema repair loop or fallback to a deterministic safe default.

---

## 2. ADVANCED RAG ARCHITECTURE
Do not rely on naive vector similarity search alone:
1. **Document Chunking**:
   - Use structure-aware chunking (Markdown headers, AST code parser, semantic sentence boundaries).
   - Maintain 15-20% chunk overlap to preserve cross-boundary context.
2. **Hybrid Search (Dense + Sparse)**:
   - Combine dense vector embeddings (cosine similarity) with sparse BM25 keyword matching using Reciprocal Rank Fusion (RRF).
3. **Cross-Encoder Re-Ranking**:
   - Pass top-20 retrieved candidates through a cross-encoder model (e.g., Cohere Rerank, BGE-Reranker) to select the true top-3 most relevant passages.
4. **Context Isolation**:
   - Wrap retrieved context in explicit delimiters (`<context>...</context>`) with instructions to cite chunk source IDs.

---

## 3. AGENTIC LOOPS & RECURSION GUARDRAILS
- **Execution Ceilings**:
  Hardcode a maximum loop iteration counter (e.g. `max_turns = 10`) and a total token budget to prevent runaway API billing loops.
- **Human-in-the-Loop Triggers**:
  Autonomous tools must require explicit human confirmation for destructive actions (database drops, cloud resource deletions, automated mass emails).
- **Prompt Injection Defense**:
  Sanitize untrusted user inputs before injecting into system prompts. Treat all external tool responses (web scrapes, emails) as potentially malicious.
