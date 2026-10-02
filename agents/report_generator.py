"""Generate the final structured research report using Google Gemini."""

from google import genai
from google.genai import types


# Default model — stable, fast, and widely available
DEFAULT_MODEL = "gemini-3.5-flash-lite"


def main_rg(api_key, refined_cntnt, system_persona, query, sources):
    """
    Generate the final research report using Gemini.

    Args:
        api_key: Google Gemini API key.
        refined_cntnt: Refined content from info_refiner.
        system_persona: System prompt guiding report structure.
        query: Original user query.
        sources: List of source URLs.

    Returns:
        Final report as a plain string.

    Raises:
        ValueError: If required inputs are missing.
        RuntimeError: If the Gemini API call fails.
    """
    if not refined_cntnt:
        raise ValueError("Refined content is empty — nothing to generate from.")
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")
    if not api_key:
        raise ValueError("Gemini API key is missing.")

    try:
        client = genai.Client(api_key=api_key)

        prompt = (
            f"Query: {query}\n\n"
            f"Refined_Content: {refined_cntnt}\n\n"
            f"Sources: {sources}"
        )

        response = client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_persona,
                temperature=0.4,
            ),
        )

        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise RuntimeError("Gemini returned an empty report.")

        return text

    except Exception as e:
        raise RuntimeError(f"Report generation failed: {e}")