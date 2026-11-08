"""Knowledge Base Policy Retrieval Tool using Vector Similarity."""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src.config import KNOWLEDGE_BASE_DIR
from src.state import RetrievedPolicyChunk


class PolicyKnowledgeRetriever:
    """Retrieves authoritative policy documentation using semantic and keyword matching."""

    def __init__(self, kb_dir: Optional[Path] = None):
        self.kb_dir = kb_dir or KNOWLEDGE_BASE_DIR
        self.chunks: List[Dict[str, Any]] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self._load_and_index_policies()

    def _load_and_index_policies(self) -> None:
        """Parse all markdown files in the knowledge base and index them by section."""
        self.chunks.clear()
        if not self.kb_dir.exists():
            return

        md_files = sorted(list(self.kb_dir.glob("*.md")))
        for file_path in md_files:
            content = file_path.read_text(encoding="utf-8")
            
            # Extract Policy Title and Policy ID
            title_match = re.search(r"^#\s+(.+?)(?:\s*\((POL-[A-Z]+-\d+)\))?$", content, re.MULTILINE)
            policy_title = title_match.group(1).strip() if title_match else file_path.stem.replace("_", " ").title()
            policy_id = title_match.group(2) if (title_match and title_match.group(2)) else f"POL-{file_path.stem[:3].upper()}"

            # Split by markdown H2 sections
            sections = re.split(r"\n(?=##\s+)", content)
            for sec in sections:
                sec = sec.strip()
                if not sec:
                    continue
                lines = sec.split("\n")
                sec_header = lines[0].replace("##", "").strip() if lines[0].startswith("##") else "General Overview"
                body = "\n".join(lines[1:]).strip() if len(lines) > 1 else lines[0]

                # Identify autonomous limits
                auto_limit = None
                limit_match = re.search(r"\$(\d+(?:\.\d{2})?)", body)
                if limit_match and "autonomous" in body.lower():
                    try:
                        auto_limit = float(limit_match.group(1))
                    except ValueError:
                        auto_limit = None

                chunk_entry = {
                    "policy_id": policy_id,
                    "title": f"{policy_title} - {sec_header}",
                    "section": sec_header,
                    "text": sec,
                    "body": body,
                    "autonomous_limit": auto_limit,
                    "file_name": file_path.name
                }
                self.chunks.append(chunk_entry)

        # Index chunks with TF-IDF
        if self.chunks:
            corpus = [f"{c['title']}\n{c['text']}" for c in self.chunks]
            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def retrieve(self, query: str, top_k: int = 3, threshold: float = 0.05) -> List[RetrievedPolicyChunk]:
        """Search policy chunks relevant to the given query."""
        if not self.chunks or self.vectorizer is None or self.tfidf_matrix is None:
            return []

        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.tfidf_matrix)[0]

        # Rank indices by score descending
        ranked_indices = scores.argsort()[::-1]

        results: List[RetrievedPolicyChunk] = []
        for idx in ranked_indices[:top_k]:
            score = float(scores[idx])
            if score < threshold and len(results) >= 1:
                break
            chunk = self.chunks[idx]
            results.append({
                "policy_id": chunk["policy_id"],
                "title": chunk["title"],
                "relevance_score": round(score, 4),
                "excerpt": chunk["body"][:300] + ("..." if len(chunk["body"]) > 300 else ""),
                "autonomous_limit": chunk["autonomous_limit"],
                "consequential_trigger": "Human approval required above limit or for security/legal terms"
            })

        return results


# Global singleton instance for easy import
policy_retriever_tool = PolicyKnowledgeRetriever()
