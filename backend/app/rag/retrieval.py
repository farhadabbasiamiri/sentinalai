from pathlib import Path
import re

POLICY_PATH = Path(__file__).resolve().parents[1] / "policies" / "governance.md"


def search_policies(query: str, limit: int = 4):
    if not POLICY_PATH.exists():
        return []
    text = POLICY_PATH.read_text(encoding="utf-8")
    sections = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    terms = {term.lower() for term in re.findall(r"[a-zA-Z0-9_-]{3,}", query)}
    ranked = []
    for section in sections:
        lines = section.strip().splitlines()
        if not lines or not lines[0].startswith("## "):
            continue
        section_terms = set(re.findall(r"[a-zA-Z0-9_-]{3,}", section.lower()))
        score = len(terms & section_terms)
        if score:
            ranked.append((score, lines[0][3:], section.strip()))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [{"source": "backend/app/policies/governance.md", "section": title, "excerpt": body, "retrieval": "keyword"} for _, title, body in ranked[:limit]]
