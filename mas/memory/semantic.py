"""
Tier 3: Semantic Memory (Domain Knowledge & Semantic Store).
Stores domain axioms, design patterns, coding standards, and historical post-mortems.
Provides keyword & semantic similarity retrieval.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SemanticDocument(BaseModel):
    doc_id: str
    category: str  # "coding_guidelines", "domain_ontology", "architecture_pattern", "post_mortem"
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)


class SemanticMemory:
    def __init__(self):
        self._documents: Dict[str, SemanticDocument] = {}
        self._load_baseline_guidelines()

    def _load_baseline_guidelines(self) -> None:
        self.add_document(
            doc_id="SOLID_CLEAN_CODE",
            category="coding_guidelines",
            title="Clean Code & SOLID Design Principles",
            content="""
1. Single Responsibility: Every class/function must have one reason to change.
2. Open/Closed: Software entities should be open for extension, closed for modification.
3. Liskov Substitution: Subtypes must be substitutable for base types.
4. Interface Segregation: Clients should not be forced to depend on interfaces they do not use.
5. Dependency Inversion: Depend upon abstractions, not concretions.
            """,
            tags=["clean_code", "solid", "standards"],
        )
        self.add_document(
            doc_id="UBIQUITOUS_LANGUAGE",
            category="domain_ontology",
            title="Enterprise Domain Ubiquitous Language",
            content="""
- Task: Scoped work item with defined blast radius.
- PRD: Formal requirement specification with Given/When/Then.
- ADR: Architectural decision record evaluating trade-offs.
- Blackboard: Versioned git-backed artifact repository.
            """,
            tags=["domain", "ddd", "language"],
        )

    def add_document(
        self, doc_id: str, category: str, title: str, content: str, tags: Optional[List[str]] = None
    ) -> None:
        self._documents[doc_id] = SemanticDocument(
            doc_id=doc_id, category=category, title=title, content=content, tags=tags or []
        )

    def query(
        self, query_text: str, category: Optional[str] = None, limit: int = 5
    ) -> List[SemanticDocument]:
        """
        Token-matching and tag-scoring semantic search.
        """
        tokens = set(query_text.lower().replace(",", " ").replace(".", " ").split())
        scored: List[tuple[int, SemanticDocument]] = []

        for doc in self._documents.values():
            if category and doc.category != category:
                continue

            score = 0
            doc_text = (doc.title + " " + doc.content + " " + " ".join(doc.tags)).lower()
            for token in tokens:
                if len(token) > 2 and token in doc_text:
                    score += 1
            if score > 0 or not tokens:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:limit]]
