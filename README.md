# 🎓 Moodle Intelligence Tracker

> An AI-powered academic monitoring system that watches your Moodle courses 24/7 and delivers smart Arabic reports directly to Telegram — so you never miss a lecture, assignment, or deadline again.

---

## 📌 The Problem

At Al-Aqsa University in Gaza, education has moved entirely online. Professors upload files, assignments, and quizzes to Moodle at any time — no fixed schedule, no notifications.

Checking 8 courses manually every day is exhausting and unreliable:
- Moodle is slow and heavy on mobile
- New content gets buried across multiple sections
- Missing a deadline means losing marks
- Searching for a specific file link wastes time

**I needed something that watches Moodle for me.**

---

## ✨ The Solution

A two-component intelligent system:

### 1. 📊 Automated Tracker (GitHub Actions)
Runs every 6 hours → scrapes all enrolled courses → detects new content → generates an AI-written Arabic report → sends it to Telegram.

### 2. 💬 Interactive Chatbot (Render + Flask)
A Telegram bot that answers questions about your courses in real-time:
- *"Send me the link to the Visual Programming assignment"*
- *"What's my next deadline?"*
- *"Show me all files from the Automata course"*

---

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| Web Scraping | Python + BeautifulSoup4 |
| AI Reporting | Groq API (Llama 3.1 8B) |
| Automation | GitHub Actions (Serverless) |
| Chatbot Backend | Flask + Render |
| Notifications | Telegram Bot API |
| State Management | JSON-based change detection |
| Routing | Two-Step LLM Router |

---

## 🧠 Architecture

```
┌─────────────────────────────────────────┐
│           GitHub Actions                │
│         (Every 6 Hours)                 │
│                                         │
│  Login → Scrape 8 Courses → Compare    │
│  with state.json → Detect New Items    │
│  → Generate Arabic Report via Groq     │
│  → Send to Telegram → Save state.json  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│         Telegram Chatbot                │
│         (Render - Always On)            │
│                                         │
│  User Question                          │
│       ↓                                 │
│  Step 1: LLM Router (~100 tokens)      │
│  Identifies which course is relevant   │
│       ↓                                 │
│  Step 2: LLM Answer (~800 tokens)      │
│  Responds with targeted data only      │
│                                         │
│  Result: 85% token reduction vs        │
│  sending all data at once              │
└─────────────────────────────────────────┘
```

---

## 💡 Key Technical Decisions

**Why HTML Scraping instead of Moodle API?**
The university has Web Services disabled — HTML scraping was the only viable approach.

**Why Groq instead of OpenAI?**
Free tier, fast inference, strong Arabic support, and no geographic restrictions.

**Why GitHub Actions instead of a dedicated server?**
The tracker only needs to run at scheduled intervals. GitHub Actions is simpler, more reliable, and completely free.

**Why JSON Routing instead of Vector RAG?**
Our data is structured JSON — not unstructured long-form text. A Two-Step LLM Router is more accurate and uses 85% fewer tokens than embedding-based retrieval for this use case.

---

## 📱 What It Looks Like

**Automated Report (every 6 hours):**
```
🎓 جامعة الأقصى | مساقاتي
🕐 الثلاثاء 05/05/2026 ─ 09:00

📖 نظرية الأتمتة
🆕 جديد:
  📎 سلايدات الفصل الثاني ← رابط
  📝 واجب 2 ⏰ 08/05
```

**Chatbot Interaction:**
```
User: واجب الاندرويد

Bot: Assignment 1 - Onboarding Screens
     موعد التسليم: الجمعة 8 مايو، 11:59 PM
     الرابط: moodle.alaqsa.edu.ps/mod/assign/...
```

---

## ⚙️ Setup

### Environment Variables

| Variable | Description |
|----------|-------------|
| `MOODLE_USER` | Your university student ID |
| `MOODLE_PASS` | Your Moodle password |
| `TG_TOKEN` | Telegram Bot token |
| `TG_CHAT_ID` | Your Telegram chat ID |
| `GROQ_API_KEY` | Groq API key |
| `GH_TOKEN` | GitHub Personal Access Token |
| `GH_REPO` | Your repo (username/repo-name) |

### Deployment

**Tracker:** Add variables as GitHub Actions Secrets → run the workflow.

**Chatbot:** Deploy `bot.py` to Render as Web Service → set webhook:
```
https://api.telegram.org/bot{TOKEN}/setWebhook?url=https://your-app.onrender.com/webhook
```

---

## 📁 Project Structure

```
MoodleTracker/
├── main.py          ← Orchestrator
├── scraper.py       ← Moodle HTML scraper
├── notifier.py      ← AI report generator
├── state.py         ← Change detection
├── config.py        ← Environment config
├── bot.py           ← Telegram chatbot
├── requirements.txt
└── .github/
    └── workflows/
        └── tracker.yml
```

---

## 🔮 Roadmap

- [ ] Multi-user support
- [ ] Web dashboard
- [ ] Assignment submission reminders
- [ ] Grade tracking

---

## 👩‍💻 Built By

**Aseel Ali** — AI Assistant Developer & CS Student  
Al-Aqsa University, Gaza, Palestine  
Specializing in RAG Systems, Document Intelligence & Multilingual LLM Applications

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Aseel_Ali-blue)]([https://linkedin.com/in/aseel-ali](https://www.linkedin.com/in/aseel-ali-872b343b2?utm_source=share_via&utm_content=profile&utm_medium=member_android))
[![GitHub](https://img.shields.io/badge/GitHub-Asil--Ali-black)](https://github.com/Asil-Ali)
