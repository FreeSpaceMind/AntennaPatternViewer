"""
Full-text search index for help documentation.
Provides fast searching across all markdown documentation files from
AntennaPatternViewer, FarFieldSpherical, and SphericalWaveExpansion.

Adapted from UmbraAntennaDesigner's help search system.
"""

import re
import logging
from typing import List, Tuple, Dict, Set
from collections import defaultdict

from .help_content import get_all_documents, load_document

logger = logging.getLogger(__name__)


class HelpSearchIndex:
    """
    Inverted index for documentation search.

    Builds an index of all words in documentation files and provides
    fast searching with relevance ranking.
    """

    STOPWORDS: Set[str] = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
        'ought', 'used', 'and', 'or', 'but', 'if', 'then', 'else', 'when',
        'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into',
        'through', 'during', 'before', 'after', 'above', 'below', 'to',
        'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under',
        'again', 'further', 'once', 'here', 'there', 'where', 'why', 'how',
        'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
        'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
        'of', 'this', 'that', 'these', 'those', 'it', 'its'
    }

    def __init__(self):
        """Initialize empty search index."""
        # word -> list of (doc_key, position, char_pos)
        self.index: Dict[str, List[Tuple[str, int, int]]] = defaultdict(list)
        # doc_key -> full content
        self.documents: Dict[str, str] = {}
        # doc_key -> metadata (title, category)
        self.metadata: Dict[str, Dict[str, str]] = {}
        self.is_built = False

    def build_index(self) -> int:
        """
        Build search index from all documentation files.

        Returns:
            Number of documents indexed
        """
        self.index.clear()
        self.documents.clear()
        self.metadata.clear()

        doc_count = 0

        for doc_key, title, category in get_all_documents():
            content = load_document(doc_key)

            if content.startswith("Document not found:") or content.startswith("Error"):
                continue

            self.documents[doc_key] = content
            self.metadata[doc_key] = {'title': title, 'category': category}

            words = self._tokenize(content)
            for position, word in enumerate(words):
                char_pos = content.lower().find(word)
                self.index[word].append((doc_key, position, max(0, char_pos)))

            doc_count += 1

        self.is_built = True
        logger.debug(f"Search index built: {doc_count} documents, {len(self.index)} terms")

        return doc_count

    def search(self, query: str, max_results: int = 20) -> List[Tuple[str, str, str, str, float]]:
        """
        Search for query terms in documentation.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of (doc_key, title, category, snippet, score) tuples,
            sorted by relevance score (highest first)
        """
        if not self.is_built:
            self.build_index()

        query_words = self._tokenize(query)
        if not query_words:
            return []

        doc_scores: Dict[str, float] = defaultdict(float)
        doc_matches: Dict[str, Set[str]] = defaultdict(set)

        for word in query_words:
            # Exact match
            for doc_key, position, char_pos in self.index.get(word, []):
                doc_scores[doc_key] += 1.0
                doc_matches[doc_key].add(word)

            # Prefix match for partial words (3+ chars)
            if len(word) >= 3:
                for indexed_word in self.index.keys():
                    if indexed_word.startswith(word) and indexed_word != word:
                        for doc_key, position, char_pos in self.index[indexed_word]:
                            doc_scores[doc_key] += 0.5

        # Boost for matching multiple query words
        for doc_key in doc_scores:
            match_ratio = len(doc_matches[doc_key]) / len(query_words)
            doc_scores[doc_key] *= (1 + match_ratio)

        # Boost for title matches
        for doc_key, meta in self.metadata.items():
            title_lower = meta['title'].lower()
            for word in query_words:
                if word in title_lower:
                    doc_scores[doc_key] *= 1.5

        ranked = sorted(doc_scores.items(), key=lambda x: -x[1])

        results = []
        for doc_key, score in ranked[:max_results]:
            meta = self.metadata.get(doc_key, {})
            title = meta.get('title', doc_key)
            category = meta.get('category', '')
            snippet = self._get_snippet(doc_key, query_words)
            results.append((doc_key, title, category, snippet, score))

        return results

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into searchable words."""
        text = text.lower()
        words = re.findall(r'\b[a-z0-9]+\b', text)
        words = [w for w in words if w not in self.STOPWORDS and len(w) >= 2]
        return words

    def _get_snippet(self, doc_key: str, query_words: List[str],
                     context_chars: int = 200) -> str:
        """Extract context snippet around first match."""
        content = self.documents.get(doc_key, "")
        if not content:
            return ""

        content_lower = content.lower()

        best_pos = len(content)
        for word in query_words:
            pos = content_lower.find(word)
            if 0 <= pos < best_pos:
                best_pos = pos

        if best_pos >= len(content):
            return content[:context_chars].strip() + "..."

        start = max(0, best_pos - context_chars // 3)
        end = min(len(content), best_pos + context_chars * 2 // 3)

        if start > 0:
            while start > 0 and content[start - 1].isalnum():
                start -= 1
            while start < best_pos and content[start] in ' \n\t':
                start += 1

        if end < len(content):
            while end < len(content) and content[end - 1].isalnum():
                end += 1

        snippet = content[start:end].strip()
        snippet = re.sub(r'\s+', ' ', snippet)

        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    def get_suggestions(self, partial: str, max_suggestions: int = 10) -> List[str]:
        """Get word suggestions for autocomplete."""
        if not self.is_built:
            self.build_index()

        partial = partial.lower()
        if len(partial) < 2:
            return []

        suggestions = []
        for word in self.index.keys():
            if word.startswith(partial):
                score = len(self.index[word])
                suggestions.append((word, score))

        suggestions.sort(key=lambda x: -x[1])
        return [word for word, score in suggestions[:max_suggestions]]
