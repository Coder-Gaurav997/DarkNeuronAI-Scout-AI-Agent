"""Refine scraped web content into a focused, query-relevant summary using Groq."""

from groq import Groq


# Fast, reliable Groq model for text refinement
DEFAULT_MODEL = "openai/gpt-oss-120b"


def info_refiner(web_content, query, system_persona, api_key):
    """
    Refine web content into a clean, query-focused summary using Groq.

    Args:
        web_content: Raw scraped content from the web extractor.
        query: Original user query.
        system_persona: System prompt guiding refinement.
        api_key: Groq API key.

    Returns:
        Refined content as a plain string.

    Raises:
        ValueError: If inputs are missing.
        RuntimeError: If the Groq API call fails.
    """
    if not web_content:
        raise ValueError("Web content is empty — nothing to refine.")
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")
    if not api_key:
        raise ValueError("Groq API key is missing.")

    try:
        client = Groq(api_key=api_key)

        completion = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_persona},
                {
                    "role": "user",
                    "content": f"Query: {query}\n\nContent: {web_content}",
                },
            ],
            temperature=0.3,
            max_tokens=1200,
            top_p=0.9,
        )

        result = completion.choices[0].message.content
        if not result or not result.strip():
            raise RuntimeError("Groq returned an empty response.")

        return result

    except Exception as e:
        raise RuntimeError(f"Info refinement failed: {e}") from e


def main_ir(web_content, query, system_persona, api_key):
    """
    Public entry point — refine web content using Groq.

    Returns:
        Refined content string.
    """
    return info_refiner(web_content, query, system_persona, api_key)