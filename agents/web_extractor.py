"""Web search and content cleaning using Exa AI."""

import re
from exa_py import Exa


# Boilerplate words filtered out of scraped content
BAD_WORDS = set(
    "subscribe,login,sign in,register,cookie,privacy,terms,advertisement,"
    "follow us,share,related,read more,trending,breaking,newsletter,copyright,"
    "contact,about us,facebook,instagram,twitter,linkedin,youtube,reddit,menu,search".split(",")
)


def search_web(query: str, api_key: str):
    """
    Search the web using Exa's semantic search.

    Args:
        query: User's search query.
        api_key: Exa API key.

    Returns:
        Exa search response object.

    Raises:
        ValueError: If query is empty or api_key is missing.
        RuntimeError: If Exa search fails.
    """
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")
    if not api_key:
        raise ValueError("Exa API key is missing.")

    try:
        exa = Exa(api_key)
        # "auto" lets Exa pick the best strategy for the query
        return exa.search(query, num_results=4, type="auto")
    except Exception as e:
        raise RuntimeError(f"Exa search failed: {e}") from e


def clean_results(results):
    """
    Remove boilerplate, duplicate, and irrelevant lines from Exa results.

    Args:
        results: List of Exa result objects.

    Returns:
        Tuple of (articles_string, sources_list).
    """
    articles, sources = [], []

    for page in results:
        if not getattr(page, "text", None):
            continue

        cleaned, seen = [], set()

        for line in map(str.strip, page.text.splitlines()):
            if (
                not line
                or line.lower() == "none"
                or len(line.split()) < 4
                or line.startswith("#")
                or re.fullmatch(r"https?://\S+", line)
                or any(word in line.lower() for word in BAD_WORDS)
            ):
                continue

            if line.lower() not in seen:
                seen.add(line.lower())
                cleaned.append(line)

        text = " ".join(cleaned)
        text = " ".join(text.split()[:250])  # keep first 250 words

        articles.append({
            "id": len(articles) + 1,
            "title": page.title,
            "text": text,
        })

        # ✅ FIX: keep the FULL url (with https://) so the frontend can
        # render it as a clickable <a> tag.
        if page.url:
            sources.append(page.url)


    return str(articles), sources


def main_we(query: str, api_key: str):
    """
    Search the web and return cleaned content + sources.

    Args:
        query: User's search query.
        api_key: Exa API key.

    Returns:
        Tuple of (cleaned_articles_str, sources_list).

    Raises:
        RuntimeError: If no usable content was retrieved.
    """
    try:
        results = search_web(query, api_key)
        articles, sources = clean_results(results.results)

        if not articles:
            raise RuntimeError("No usable content was extracted from the web results.")

        return articles, sources
    except (ValueError, RuntimeError):
        raise
    except Exception as e:
        raise RuntimeError(f"Web extraction failed: {e}") from e