"""API keys for Scout's external services.

On the deployment platform (Render / HF / Fly), set these as
environment variables — never hardcode them in this file.
"""

import os

Groq_API = os.environ.get("GROQ_API_KEY", "")
Exa_API = os.environ.get("EXA_API_KEY", "")
Gemini_API = os.environ.get("GEMINI_API_KEY", "")