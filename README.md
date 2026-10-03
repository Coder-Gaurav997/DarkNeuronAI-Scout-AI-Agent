# 🛰️ DarkNeuronAI Scout

> **Autonomous Research & Report Generation AI Agent**

"Built under the supervision of **Gaurav Pandey** — Founder & Chief AI Officer, DarkNeuronAI"

Scout is a production-ready AI agent that autonomously researches any topic on the open web, filters the relevant information, and generates a well-sourced analytical report — all in seconds.

---

## ✨ Features

- 🔍 **Autonomous web research** — Retrieves and parses pages via Exa
- 🧠 **LLM-powered refinement** — Filters noise with Groq
- 📝 **Structured report generation** — Composes final briefs via Gemini
- ⚡ **Live streaming status** — Real-time SSE updates during pipeline execution
- 🌗 **Light & Dark themes** — With animated gradient accents
- 🔐 **Supabase Auth** — Email + password signup and login
- 📊 **Daily usage limits** — 3 reports per user per day (server-enforced)
- 👤 **User profiles** — View/edit name, change password, sign out, delete account
- 💬 **ChatGPT-style interface** — Centered chat column, gradient bubbles, logo avatars

---

## 🏗️ Architecture

```
┌─────────────────┐      ┌──────────────┐      ┌──────────────────┐
│   Frontend      │─────▶│  Flask API   │─────▶│   Scout Pipeline │
│   (index.html)  │      │  (app.py)    │      │  we → ir → rg    │
└─────────────────┘      └──────┬───────┘      └──────────────────┘
        │                       │
        │                       ▼
        │                ┌──────────────┐
        │                │   Supabase   │
        └───────────────▶│  Auth + DB   │
     (JWT via Supabase)  └──────────────┘
```

- **Frontend** — Authenticates with Supabase → gets a JWT → sends it to the backend
- **Backend** — Verifies the JWT → checks daily usage → runs the pipeline → streams results
- **Supabase** — Handles user accounts (bcrypt-hashed passwords) and daily counters

---

## 📁 Project Structure

```
scout-ai/
├── app.py                  Flask backend (SSE, auth, rate limiting)
├── config.py               Supabase secrets (gitignored)
├── requirements.txt
├── .gitignore
├── README.md
│
├── frontend/
│   ├── index.html          Complete single-file frontend
│   └── scout-logo.png      Circular logo
│
├── utils/
│   ├── __init__.py
│   ├── configs.py          API keys for Exa, Groq, Gemini
│   └── system_prompts.py   LLM prompts
│
├── agents/
│   ├── __init__.py
│   ├── web_extractor.py
│   ├── info_refiner.py
│   └── report_generator.py
│
├── tests/
    └── test_pipeline.py
```

---

## 🔌 API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/` | Serve `index.html` |
| `GET` | `/<path>` | Serve static files (logo, etc.) |
| `GET` | `/api/config` | Return Supabase URL + anon key |
| `POST` | `/api/usage` | Return today's usage count for user |
| `POST` | `/api/research` | **SSE stream** — runs pipeline |
| `POST` | `/api/delete-account` | Delete user + usage rows |

### SSE Event Format

```
data: {"type":"status","message":"Searching The Web..."}

data: {"type":"status","message":"9 Web Pages Found!"}

data: {"type":"status","message":"Filtering Relevant Info..."}

data: {"type":"status","message":"Generating The Final Report..."}

data: {"type":"report","report":"...","sources":[...],"used":1,"limit":3}

data: {"type":"error","message":"..."}
```

---

## 🔐 Authentication Flow

```
Signup:
  Frontend → sb.auth.signUp(email, password)
         → Supabase stores bcrypt hash
         → Session returned immediately
         → Username onboarding modal
         → Save to user_metadata.username

Login:
  Frontend → sb.auth.signInWithPassword(email, password)
         → Supabase validates hash
         → Session returned

Every request:
  Frontend → fetch('/api/research', { Authorization: 'Bearer <JWT>' })
         → Backend verifies JWT via supabase.auth.get_user(token)
         → Identifies user → enforces daily limit
```

---

## 📊 Daily Limit Enforcement

- **3 reports per user per day**
- Counter lives in `daily_usage` table keyed by `(user_id, day)`
- Incremented **only after** a successful pipeline run
- Cannot be bypassed via:
  - Clearing localStorage ✅ (server is source of truth)
  - Incognito mode ✅ (user ID comes from JWT, not storage)
  - Different browser ✅ (same account = same ID)
  - Different device ✅ (same account = same ID)

---

## 🗄️ Database Schema

See `db/schema.sql` for the full setup. Key table:

```sql
CREATE TABLE public.daily_usage (
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  day DATE NOT NULL DEFAULT CURRENT_DATE,
  count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, day)
);
```

---

## 🧪 Testing the Pipeline

Run the pipeline directly without Flask:

```bash
python tests/test_pipeline.py
```

This bypasses auth and just runs `main_we → main_ir → main_rg` to verify your API keys work.

---

## 🚢 Deployment

### Vercel (Frontend + Serverless Backend)

1. Push your code to GitHub
2. Import the repo at [vercel.com](https://vercel.com)
3. Set environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_KEY`
   - `EXA_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`
4. Update `config.py` to read from `os.environ`
5. Set your Vercel domain in **Supabase → Authentication → URL Configuration**

### Hugging Face Spaces (Backend)

1. Create a new **Docker** or **Streamlit** Space
2. Add the same environment variables in **Space Settings**
3. Deploy

See `docs/DEPLOYMENT.md` for the full guide.

---

## 🐛 Troubleshooting

| Error | Fix |
|-------|-----|
| `Email signups are disabled` | Enable Email provider in Supabase |
| `Email not confirmed` | Turn off Confirm email + run SQL to confirm existing users |
| `new row violates row-level security policy` | Backend is using anon key — switch to service_role key |
| `Config load failed` | Check `/api/config` route is running |
| Pipeline hangs | Verify Exa/Groq/Gemini API keys |

See `docs/TROUBLESHOOTING.md` for more.

---

## 📄 `.gitignore`

```
# Secrets
config.py
.env
*.log

# Python
__pycache__/
*.py[cod]
venv/
env/
.pytest_cache/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
```

---

## 📄 `requirements.txt`

```
flask
flask-cors
supabase
python-dotenv
```

---

## 📄 `.env.example`

```
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
EXA_API_KEY=...
GROQ_API_KEY=...
GEMINI_API_KEY=...
```

---

## 📄 `db/schema.sql`

```sql
-- Daily usage counter (one row per user per day)
CREATE TABLE IF NOT EXISTS public.daily_usage (
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  day DATE NOT NULL DEFAULT CURRENT_DATE,
  count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, day)
);

CREATE INDEX IF NOT EXISTS idx_daily_usage_user_day
  ON public.daily_usage (user_id, day);

-- Row Level Security
ALTER TABLE public.daily_usage ENABLE ROW LEVEL SECURITY;

-- Users can read their own usage
CREATE POLICY "Users read own usage"
  ON public.daily_usage FOR SELECT
  USING (auth.uid() = user_id);

-- Users can insert their own usage (needed if frontend ever writes; safe either way)
CREATE POLICY "Users insert own usage"
  ON public.daily_usage FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Users can update their own usage
CREATE POLICY "Users update own usage"
  ON public.daily_usage FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
```

> ⚠️ **Note:** The service_role key used by the backend **bypasses RLS entirely**, so these policies mainly protect against frontend abuse.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Vanilla HTML / CSS / JS |
| **Auth** | Supabase Auth (email + password, bcrypt) |
| **Database** | Supabase Postgres |
| **Backend** | Flask + Flask-CORS |
| **Streaming** | Server-Sent Events (SSE) |
| **Web Search** | Exa |
| **Info Refining** | Groq (LLaMA) |
| **Report Writing** | Google Gemini |
| **Deployment** | Vercel / Hugging Face Spaces |

---

## 🔑 API Keys Required

| Key | Where to get it | Cost |
|-----|-----------------|------|
| Supabase URL + keys | [supabase.com](https://supabase.com) | Free (50k MAU) |
| Exa API | [exa.ai](https://exa.ai) | Free tier available |
| Groq API | [console.groq.com](https://console.groq.com) | Free tier available |
| Gemini API | [aistudio.google.com](https://aistudio.google.com) | Free tier available |

---

## 📜 License

© 2025 DarkNeuronAI. All rights reserved.

---

## 👤 Author

**Gaurav Pandey**
Founder & Chief AI Officer — DarkNeuronAI

---

## 🙏 Acknowledgements

Built with the support of:
- Exa — semantic web search
- Groq — fast LLM inference
- Google Gemini — report generation
- Supabase — auth + database
