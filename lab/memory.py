"""
Lab 7 Module 4: Persistent State Management & Local Document Retrieval (RAG)
モジュール 4：永続化状態管理とローカルRAG検索
"""
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"


# ----------------------------------------------------------------- provided helpers
def default_db_path() -> str:
    """DB location: $LAB_DB_PATH if set, otherwise <project>/data/memory.sqlite3.
    Independent of the current working directory."""
    return os.environ.get("LAB_DB_PATH") or str(PROJECT_ROOT / "data" / "memory.sqlite3")


def _resolve(db_path: Optional[str]) -> str:
    return db_path or default_db_path()


def _require(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def init_db(db_path: Optional[str] = None) -> str:
    """Create the preferences table if needed and return the DB path actually used."""
    path = _resolve(db_path)
    parent = os.path.dirname(path)
    if parent:  # a bare filename like "mem.sqlite3" has no folder to create
        os.makedirs(parent, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                user_id TEXT NOT NULL,
                scope TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                evidence TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, scope, key)
            )
        """)
    return path


def get_preferences(user_id: str, scope: str, db_path: Optional[str] = None) -> Dict[str, str]:
    path = init_db(db_path)
    with closing(sqlite3.connect(path)) as conn:
        rows = conn.execute(
            "SELECT key, value FROM preferences WHERE user_id = ? AND scope = ? ORDER BY key",
            (user_id, scope),
        ).fetchall()
    return {k: v for k, v in rows}


def get_preference_details(user_id: str, scope: str, db_path: Optional[str] = None) -> List[Dict[str, str]]:
    """Like get_preferences, but includes evidence and timestamps (for auditing what was remembered)."""
    path = init_db(db_path)
    with closing(sqlite3.connect(path)) as conn:
        rows = conn.execute(
            "SELECT key, value, evidence, updated_at FROM preferences "
            "WHERE user_id = ? AND scope = ? ORDER BY key",
            (user_id, scope),
        ).fetchall()
    return [{"key": k, "value": v, "evidence": e or "", "updated_at": t} for k, v, e, t in rows]


# ----------------------------------------------------------------- student tasks
def set_preference(user_id: str, scope: str, key: str, value: str, evidence: str = "",
                   db_path: Optional[str] = None) -> None:
    """
    TODO [Task 4.1]: Persistent Scoped State in SQLite (Week 6 State / Memory Concepts)
    - user_id, scope, key and value must be non-empty strings (use _require) -> else ValueError.
    - path = init_db(db_path), then INSERT the row keyed on (user_id, scope, key).
      If it already exists, update value, evidence and updated_at (ON CONFLICT ... DO UPDATE).
    - Always use "?" placeholders, never f-strings, in SQL.
    """
    # --- STUDENT IMPLEMENTATION START ---
    user_id = _require(user_id, "user_id")
    scope = _require(scope, "scope")
    key = _require(key, "key")
    value = _require(value, "value")
    path = init_db(db_path)
    with closing(sqlite3.connect(path)) as conn, conn:  # inner "conn" commits the transaction
        conn.execute(
            """
            INSERT INTO preferences (user_id, scope, key, value, evidence, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id, scope, key) DO UPDATE SET
                value = excluded.value,
                evidence = excluded.evidence,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, scope, key, value, evidence or ""),
        )
    # --- STUDENT IMPLEMENTATION END ---


def forget_preference(user_id: str, scope: str, key: str, db_path: Optional[str] = None) -> bool:
    """
    TODO [Task 4.1]: Delete one preference. Return True if a row was deleted, False otherwise.
    Other keys, scopes and users must not be affected.
    """
    # --- STUDENT IMPLEMENTATION START ---
    path = init_db(db_path)
    with closing(sqlite3.connect(path)) as conn, conn:
        cur = conn.execute(
            "DELETE FROM preferences WHERE user_id = ? AND scope = ? AND key = ?",
            (user_id, scope, key),
        )
        return cur.rowcount > 0
    # --- STUDENT IMPLEMENTATION END ---


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "for", "from", "how", "i",
    "in", "is", "it", "me", "my", "of", "on", "or", "please", "the", "to", "what", "when",
    "where", "which", "who", "with", "you", "find", "show", "tell", "about",
}
_CJK = r"぀-ヿ㐀-䶿一-鿿ｦ-ﾟ"
_TOKEN_RE = re.compile(rf"[{_CJK}]+|[a-z0-9]+")


def tokenize(text: str) -> set:
    """
    TODO [Task 4.2]: Turn text into a SET of tokens for matching.
    - Lowercase. Split into runs of Japanese/Chinese characters and runs of [a-z0-9] (use _TOKEN_RE).
    - Latin runs: keep if not in STOPWORDS and longer than 1 character.
    - Japanese runs: add every 2-character pair (bigram), e.g. "京都の庭" -> {"京都", "都の", "の庭"};
      a single character is kept as is.
    """
    # --- STUDENT IMPLEMENTATION START ---
    tokens = set()
    for run in _TOKEN_RE.findall((text or "").lower()):
        if re.match(rf"[{_CJK}]", run):
            if len(run) == 1:
                tokens.add(run)
            else:
                tokens.update(run[i:i + 2] for i in range(len(run) - 1))
        elif len(run) > 1 and run not in STOPWORDS:
            tokens.add(run)
    return tokens
    # --- STUDENT IMPLEMENTATION END ---


def simple_keyword_rag(query: str, documents: List[str], top_k: int = 2) -> List[str]:
    """
    TODO [Task 4.2]: Local Document Retrieval (RAG - Week 2 Concept)
    - Score each document by the number of DISTINCT query tokens it contains
      (tokenize() both; repeated words must not inflate the score).
    - Drop documents with score 0. Sort by score (highest first); ties keep the original order.
    - Return at most top_k documents ([] if top_k < 1 or the query has no tokens).
    """
    # --- STUDENT IMPLEMENTATION START ---
    if top_k < 1:
        return []
    query_tokens = tokenize(query)
    if not query_tokens:
        return []
    scored = []
    for index, doc in enumerate(documents):
        score = len(query_tokens & tokenize(doc))  # distinct shared tokens only
        if score > 0:
            scored.append((score, index, doc))
    # Highest score first; ties keep the original document order.
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [doc for _, _, doc in scored[:top_k]]
    # --- STUDENT IMPLEMENTATION END ---


# ----------------------------------------------------------------- provided: knowledge base
def load_knowledge(knowledge_dir: Optional[str] = None) -> List[Dict[str, str]]:
    """Split every knowledge/*.md file into chunks (one per bullet or paragraph)."""
    folder = Path(knowledge_dir) if knowledge_dir else KNOWLEDGE_DIR
    chunks = []
    for path in sorted(folder.glob("*.md")):
        title = path.stem
        for block in re.split(r"\n\s*\n|\n(?=\s*[-*] )", path.read_text(encoding="utf-8")):
            text = block.strip().lstrip("-* ").strip()
            if not text:
                continue
            if text.startswith("#"):
                title = text.lstrip("# ").strip()
                continue
            chunks.append({"source": path.name, "title": title, "text": text})
    return chunks


def search_knowledge(query: str, top_k: int = 2, knowledge_dir: Optional[str] = None) -> List[Dict[str, str]]:
    """RAG over the local knowledge/ folder. Returns chunks with their source file for citation."""
    chunks = load_knowledge(knowledge_dir)
    texts = [f"{c['title']}: {c['text']}" for c in chunks]
    hits = simple_keyword_rag(query, texts, top_k=top_k)
    return [chunks[texts.index(h)] for h in hits]


# ----------------------------------------------------------------- provided: places file (Task 4.3)
PLACES_FILE = KNOWLEDGE_DIR / "places_japan.md"
REQUIRED_PLACE_FIELDS = ["category", "highlights", "access", "cost", "best season", "source"]
_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
_FIELD_RE = re.compile(r"^\s*[-*]\s*([^:：]+)[:：]\s*(.*)$")


def parse_places(path: Optional[str] = None) -> List[Dict[str, object]]:
    """
    Parse knowledge/places_japan.md. Each place starts with a heading like
        ## Chuson-ji (中尊寺) — Hiraizumi, Iwate (岩手県平泉町)
    followed by "- Field: value" bullets. Returns one dict per place:
        {"heading", "english_name", "japanese_name", "fields": {lowercase field: value}}
    """
    file = Path(path) if path else PLACES_FILE
    if not file.exists():
        return []
    places: List[Dict[str, object]] = []
    current: Optional[Dict[str, object]] = None
    for line in file.read_text(encoding="utf-8").splitlines():
        m = _HEADING_RE.match(line)
        if m:
            heading = m.group(1)
            jp = re.search(r"[(（]([^)）]+)[)）]", heading)
            current = {
                "heading": heading,
                "english_name": re.split(r"\s*[(（]", heading, maxsplit=1)[0].strip(),
                "japanese_name": jp.group(1).strip() if jp else "",
                "fields": {},
            }
            places.append(current)
            continue
        f = _FIELD_RE.match(line)
        if current is not None and f:
            current["fields"][f.group(1).strip().lower()] = f.group(2).strip()
    return places