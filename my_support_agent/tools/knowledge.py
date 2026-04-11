"""Knowledge base search tool."""

from my_support_agent.config import get_knowledge_base


# Stop words to filter from queries
_STOP_WORDS = {"what", "is", "the", "a", "an", "how", "do", "i", "can", "to", "my", "me", "are", "for", "of", "in", "and", "or"}


def _search_sections(kb_content: str | None, query: str) -> list[str]:
    """Split knowledge base into sections and return matching ones.

    Exported for testing. The tool function below wraps this.
    """
    if not kb_content or not query or not query.strip():
        return []

    # Split by ## headers
    sections: list[str] = []
    current_section = ""
    for line in kb_content.split("\n"):
        if line.startswith("## "):
            if current_section.strip():
                sections.append(current_section.strip())
            current_section = line + "\n"
        else:
            current_section += line + "\n"
    if current_section.strip():
        sections.append(current_section.strip())

    # Tokenize query, remove stop words
    keywords = [
        w for w in query.lower().split()
        if w not in _STOP_WORDS and len(w) > 1
    ]
    if not keywords:
        # All words were stop words — use original query words
        keywords = [w for w in query.lower().split() if len(w) > 1]

    # Return sections where any keyword appears
    matches = []
    for section in sections:
        section_lower = section.lower()
        if any(kw in section_lower for kw in keywords):
            matches.append(section)

    return matches


def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for answers to customer questions.

    Use this tool when the customer asks general questions about
    JLPT levels, payment methods, enrollment process, refund policy,
    class schedules, or contact information.
    """
    kb_content = get_knowledge_base()
    matches = _search_sections(kb_content, query)

    if not matches:
        return "I don't have specific information about that. I can create a support ticket if you need help."

    return "\n\n".join(matches)
