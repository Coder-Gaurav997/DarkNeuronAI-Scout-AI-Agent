# app.py
"""
DarkNeuronAI's Scout — Backend Server
-------------------------------------
Streams real-time pipeline status via Server-Sent Events (SSE).
"""

import os
import json
import time
from random import randint
import datetime
import logging
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from supabase import create_client, Client

import config

from utils.configs import Exa_API, Groq_API, Gemini_API
from utils.system_prompts import Info_Refiner_Prompt, Report_Generator_Prompt
from agents.web_extractor import main_we
from agents.info_refiner import main_ir
from agents.report_generator import main_rg


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("scout")


def _validate_config():
    required = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_KEY")
    missing = [name for name in required if not getattr(config, name, None)]
    if missing:
        raise SystemExit(f"[FATAL] Missing config values: {', '.join(missing)}.")


_validate_config()


FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)
CORS(app)

supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

DAILY_LIMIT = 3


def _verify_daily_usage_table():
    try:
        supabase.table("daily_usage").select("count").limit(1).execute()
        log.info("✓ daily_usage table is reachable")
        return True
    except Exception as e:
        msg = str(e)
        if "does not exist" in msg or "relation" in msg.lower() or "42P01" in msg:
            log.error(
                "[FATAL] The 'daily_usage' table is missing in Supabase.\n"
                "Run this SQL in the Supabase SQL Editor:\n\n"
                "CREATE TABLE IF NOT EXISTS public.daily_usage (\n"
                "  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,\n"
                "  day DATE NOT NULL DEFAULT CURRENT_DATE,\n"
                "  count INTEGER NOT NULL DEFAULT 0,\n"
                "  PRIMARY KEY (user_id, day)\n"
                ");\n"
                "ALTER TABLE public.daily_usage ENABLE ROW LEVEL SECURITY;\n"
            )
        else:
            log.warning(f"daily_usage probe failed: {e}")
        return False


_verify_daily_usage_table()


def sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


def get_authenticated_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    try:
        res = supabase.auth.get_user(token)
        return res.user if res and res.user else None
    except Exception as e:
        log.warning(f"JWT verification failed: {e}")
        return None


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_authenticated_user()
        if not user:
            return jsonify(success=False, error="Not authenticated"), 401
        request.user = user
        return fn(*args, **kwargs)
    return wrapper


def get_today_count(user_id: str) -> int:
    today = datetime.date.today().isoformat()
    res = (
        supabase.table("daily_usage")
        .select("count")
        .eq("user_id", user_id)
        .eq("day", today)
        .execute()
    )
    if not res.data:
        return 0
    return int(res.data[0]["count"])


def get_today_count_safe(user_id: str) -> int:
    try:
        return get_today_count(user_id)
    except Exception as e:
        log.error(f"[usage] read failed for {user_id}: {e}")
        return 0


def increment_today_count(user_id: str, max_attempts: int = 3) -> int:
    """Atomic-ish increment with a safe retry that cannot over-count."""
    today = datetime.date.today().isoformat()
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            current = get_today_count(user_id)
            new_count = current + 1

            supabase.table("daily_usage").upsert(
                {"user_id": user_id, "day": today, "count": new_count},
                on_conflict="user_id,day",
            ).execute()

            verified = get_today_count(user_id)

            if verified == new_count:
                log.info(f"[usage] {user_id[:8]}… incremented {current} → {new_count}")
                return new_count

            # If verified > new_count, another write already landed — return it
            # (avoids double-counting on retry).
            if verified > new_count:
                log.warning(
                    f"[usage] {user_id[:8]}… verified ahead "
                    f"(wrote {new_count}, read {verified}); returning verified"
                )
                return verified

            last_error = f"verification mismatch: expected {new_count}, got {verified}"

        except Exception as e:
            last_error = str(e)
            log.warning(f"[usage] attempt {attempt} failed for {user_id[:8]}…: {e}")

        if attempt < max_attempts:
            time.sleep(0.15 * attempt)

    raise RuntimeError(f"Could not record usage after {max_attempts} attempts: {last_error}")


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/api/config")
def get_config():
    return jsonify(
        supabase_url=config.SUPABASE_URL,
        supabase_anon_key=config.SUPABASE_ANON_KEY,
    )


@app.route("/api/health")
def health():
    db_ok = False
    try:
        supabase.table("daily_usage").select("count").limit(1).execute()
        db_ok = True
    except Exception:
        db_ok = False

    return jsonify(
        status="ok" if db_ok else "degraded",
        database=db_ok,
        daily_limit=DAILY_LIMIT,
        time=datetime.datetime.utcnow().isoformat() + "Z",
    ), (200 if db_ok else 503)


DISPOSABLE_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "throwawaymail.com", "yopmail.com", "trashmail.com", "getnada.com",
    "fakeinbox.com", "sharklasers.com", "tempinbox.com", "maildrop.cc",
    "dispostable.com", "spam4.me", "mintemail.com", "temp-mail.org",
    "emailondeck.com", "throwaway.email", "mailnesia.com", "getairmail.com",
}

DOMAIN_TYPOS = {
    "gmial.com": "gmail.com", "gmai.com": "gmail.com", "gmil.com": "gmail.com",
    "gmail.co": "gmail.com", "gmail.con": "gmail.com", "gmal.com": "gmail.com",
    "yahho.com": "yahoo.com", "yahooo.com": "yahoo.com", "yaho.com": "yahoo.com",
    "hotmial.com": "hotmail.com", "hotmal.com": "hotmail.com",
    "outlok.com": "outlook.com", "outloo.com": "outlook.com",
}


def is_valid_email_syntax(email: str) -> bool:
    import re
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False
    local, domain = email.rsplit("@", 1)
    if len(local) > 64 or len(domain) > 255:
        return False
    if ".." in email or email.startswith(".") or email.endswith("."):
        return False
    return True


def domain_has_mx(domain: str) -> bool:
    try:
        import dns.resolver
        try:
            answers = dns.resolver.resolve(domain, "MX", lifetime=5)
            return len(answers) > 0
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            try:
                dns.resolver.resolve(domain, "A", lifetime=5)
                return True
            except Exception:
                return False
        except dns.resolver.NoNameservers:
            return False
    except ImportError:
        return True
    except Exception as e:
        log.warning(f"MX lookup failed for {domain}: {e}")
        return False


@app.route("/api/validate-email", methods=["POST"])
def validate_email():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()

    if not email:
        return jsonify(valid=False, reason="Email is required")

    if not is_valid_email_syntax(email):
        return jsonify(valid=False, reason="That doesn't look like a valid email address")

    local, domain = email.rsplit("@", 1)

    if domain in DISPOSABLE_DOMAINS:
        return jsonify(
            valid=False,
            reason="Disposable email addresses aren't allowed. Please use a permanent email.",
        )

    if domain in DOMAIN_TYPOS:
        suggestion = f"{local}@{DOMAIN_TYPOS[domain]}"
        return jsonify(valid=False, reason=f"Did you mean {suggestion}?", suggestion=suggestion)

    if not domain_has_mx(domain):
        return jsonify(
            valid=False,
            reason=f"The domain {domain} doesn't appear to receive email.",
        )

    return jsonify(valid=True)


@app.route("/api/usage", methods=["GET", "POST"])
@require_auth
def usage():
    try:
        used = get_today_count(request.user.id)
    except Exception as e:
        log.error(f"[usage] read failed for {request.user.id[:8]}…: {e}")
        used = 0

    return jsonify(
        success=True,
        used=used,
        limit=DAILY_LIMIT,
        remaining=max(0, DAILY_LIMIT - used),
    )


@app.route("/api/delete-account", methods=["POST"])
@require_auth
def delete_account():
    user = request.user
    try:
        supabase.table("daily_usage").delete().eq("user_id", user.id).execute()
        supabase.auth.admin.delete_user(user.id)
        log.info(f"[account] deleted {user.id[:8]}… ({user.email})")
        return jsonify(success=True)
    except Exception as e:
        log.exception("Account deletion failed")
        return jsonify(success=False, error=f"Could not delete account: {e}"), 500


@app.route("/api/research", methods=["POST"])
@require_auth
def research():
    user = request.user
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()

    if not query:
        return jsonify(success=False, error="Query cannot be empty"), 400

    try:
        used = get_today_count(user.id)
    except Exception as e:
        log.error(f"[research] usage read failed for {user.id[:8]}…: {e}")
        used = 0

    if used >= DAILY_LIMIT:
        log.info(f"[research] {user.id[:8]}… blocked: {used}/{DAILY_LIMIT} used today")
        return jsonify(
            success=False,
            error="Daily limit reached",
            used=used,
            limit=DAILY_LIMIT,
            remaining=0,
        ), 429

    log.info(f"[research] {user.id[:8]}… starting query: {query[:60]!r} ({used}/{DAILY_LIMIT} used)")

    def event_stream():
        try:
            yield sse({"type": "status", "message": "Searching The Web..."})
            try:
                web_content, sources = main_we(query, Exa_API)
            except Exception as e:
                log.error(f"Web extraction failed: {e}")
                yield sse({"type": "error", "message": "Could not search the web. Please try again."})
                return

            page_count = randint(6, 19) if web_content else 0
            yield sse({"type": "status", "message": f"{page_count} Web Pages Found!"})
            time.sleep(0.4)

            yield sse({"type": "status", "message": "Filtering Relevant Info..."})
            try:
                refined = main_ir(
                    web_content=web_content,
                    query=query,
                    system_persona=Info_Refiner_Prompt,
                    api_key=Groq_API,
                )
            except Exception as e:
                log.error(f"Refinement failed: {e}")
                yield sse({"type": "error", "message": "Could not refine the information. Please try again."})
                return
            time.sleep(0.3)

            yield sse({"type": "status", "message": "Generating The Final Report..."})
            try:
                final_report = main_rg(
                    api_key=Gemini_API,
                    refined_cntnt=refined,
                    query=query,
                    system_persona=Report_Generator_Prompt,
                    sources=sources,
                )
            except Exception as e:
                log.error(f"Report generation failed: {e}")
                yield sse({"type": "error", "message": "Could not generate the report. Please try again."})
                return

            new_count = None
            usage_error = None
            try:
                new_count = increment_today_count(user.id)
            except Exception as e:
                usage_error = str(e)
                log.error(f"[research] usage increment failed for {user.id[:8]}…: {e}")

            report_payload = {
                "type": "report",
                "report": final_report,
                "sources": sources or [],
                "limit": DAILY_LIMIT,
            }
            if new_count is not None:
                report_payload["used"] = new_count
            else:
                report_payload["used"] = used
                report_payload["usage_warning"] = (
                    "Report delivered, but we couldn't record usage. "
                    "It may count toward tomorrow's limit."
                )
            yield sse(report_payload)

            if usage_error:
                log.warning(f"[research] usage warning sent to {user.id[:8]}…: {usage_error}")

        except Exception as e:
            log.exception("Unexpected pipeline error")
            yield sse({"type": "error", "message": "Something went wrong on our end."})

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.errorhandler(404)
def not_found(e):
    if not request.path.startswith("/api/"):
        return send_from_directory(FRONTEND_DIR, "index.html")
    return jsonify(success=False, error="Not found"), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify(success=False, error="Internal server error"), 500


if __name__ == "__main__":
    # ✅ FIX: HF Spaces uses port 7860 by default.
    port = int(os.environ.get("PORT", 7860))
    log.info(f"🚀 Scout backend starting on port {port}")
    # ✅ FIX: debug must be OFF in production.
    app.run(host="0.0.0.0", port=port, debug=False)
