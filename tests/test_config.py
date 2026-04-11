from pathlib import Path


def test_knowledge_base_file_exists():
    """Verify the nihon-moment knowledge base file exists."""
    kb_file = (
        Path(__file__).parent.parent
        / "my_support_agent"
        / "knowledge_base"
        / "nihon-moment.md"
    )
    assert kb_file.exists(), f"Knowledge base file not found: {kb_file}"
