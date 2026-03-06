"""
Central configuration for the Market Research Tool.
Copy .env.example to .env and fill in your credentials.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Email (SMTP) ──────────────────────────────────────────────────────────────
EMAIL_SMTP_HOST = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
EMAIL_SMTP_PORT = int(os.getenv("EMAIL_SMTP_PORT", "587"))
EMAIL_SENDER    = os.getenv("EMAIL_SENDER", "")        # your Gmail address
EMAIL_PASSWORD  = os.getenv("EMAIL_PASSWORD", "")      # Gmail app password
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT", "")     # where to send the digest

# ── Reddit (PRAW) ─────────────────────────────────────────────────────────────
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT    = os.getenv("REDDIT_USER_AGENT", "MarketResearchBot/1.0")

# ── Scoring weights ───────────────────────────────────────────────────────────
WEIGHT_MARGIN_SIGNAL      = 0.5   # weight of margin-potential sub-score
WEIGHT_COMPETITION_SIGNAL = 0.5   # weight of low-competition sub-score

# Minimum composite score (0-100) to appear in the digest
MIN_SCORE_THRESHOLD = 40

# Maximum opportunities to include per source in the digest
MAX_PER_SOURCE = 10

# Maximum total opportunities in the digest
MAX_TOTAL = 30

# ── High-margin keyword signals ───────────────────────────────────────────────
# Presence of these words in a topic title/description boosts margin score.
HIGH_MARGIN_KEYWORDS = [
    # B2B / enterprise
    "b2b", "enterprise", "saas", "api", "platform", "workflow", "automation",
    "crm", "erp", "integration", "pipeline", "dashboard", "analytics",
    # Expensive pain points
    "compliance", "security", "gdpr", "hipaa", "audit", "payroll", "billing",
    "invoice", "tax", "legal", "contract", "hr", "recruiting", "onboarding",
    # High-value domains
    "real estate", "finance", "fintech", "insurance", "healthcare", "medical",
    "ecommerce", "logistics", "supply chain", "procurement",
    # Productised services
    "agency", "consultant", "freelance", "coaching", "course", "template",
    "plugin", "extension", "widget", "marketplace",
]

# ── Low-competition signals ───────────────────────────────────────────────────
# Reddit phrases that indicate unmet demand.
DEMAND_PHRASES = [
    "is there a tool",
    "is there an app",
    "looking for software",
    "looking for a tool",
    "wish there was",
    "anyone know of a",
    "does anyone know",
    "need a tool",
    "need software",
    "alternative to",
    "is there anything that",
    "struggling to find",
    "can't find a",
    "no good solution",
]

# Subreddits to monitor for unmet needs
TARGET_SUBREDDITS = [
    "SaaS",
    "startups",
    "entrepreneur",
    "sideproject",
    "Entrepreneur",
    "smallbusiness",
    "freelance",
    "webdev",
    "nocode",
    "indiehackers",
    "digitalnomad",
    "productivity",
    "marketing",
    "ecommerce",
]

# ── Google Trends ─────────────────────────────────────────────────────────────
# Seed keywords whose rising related queries we harvest.
TREND_SEED_KEYWORDS = [
    "saas tool",
    "automation software",
    "business software",
    "productivity app",
    "workflow automation",
    "no-code tool",
    "ai tool",
    "freelance tool",
    "small business software",
    "online business tool",
]

# Minimum growth % to consider a rising query interesting
TREND_MIN_BREAKOUT_SCORE = 50   # pytrends uses 0-100 or "Breakout" for >5000%

# ── Hacker News ──────────────────────────────────────────────────────────────
# Minimum points on a Show HN post to be considered
HN_MIN_POINTS = 10
HN_MAX_POSTS   = 200   # how many recent Show HN posts to scan

# ── Product Hunt ─────────────────────────────────────────────────────────────
# Products launched in last N days to consider "new"
PH_DAYS_WINDOW = 7
PH_MIN_VOTES   = 20
PH_MAX_POSTS   = 100
