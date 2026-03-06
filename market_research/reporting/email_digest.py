"""
HTML email digest builder and sender.

Produces a clean, mobile-friendly HTML email showing today's top
market opportunities ranked by composite score.
"""

from __future__ import annotations

import logging
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any

from market_research.config import (
    EMAIL_SMTP_HOST,
    EMAIL_SMTP_PORT,
    EMAIL_SENDER,
    EMAIL_PASSWORD,
    EMAIL_RECIPIENT,
    MAX_TOTAL,
)

logger = logging.getLogger(__name__)

# ── Source badge colours ──────────────────────────────────────────────────────
_SOURCE_COLORS = {
    "Google Trends": "#4285F4",
    "Reddit":        "#FF4500",
    "Product Hunt":  "#DA552F",
    "Hacker News":   "#FF6600",
}

_DEFAULT_COLOR = "#6C757D"


def _score_bar(score: int, color: str) -> str:
    """Return a small inline score bar HTML snippet."""
    width = max(4, score)   # minimum visible width
    return (
        f'<div style="background:#e9ecef;border-radius:4px;height:8px;width:120px;display:inline-block;">'
        f'<div style="background:{color};border-radius:4px;height:8px;width:{width}%;"></div>'
        f"</div>"
    )


def _opportunity_card(opp: Dict[str, Any], rank: int) -> str:
    source = opp["source"]
    color  = _SOURCE_COLORS.get(source, _DEFAULT_COLOR)
    url    = opp.get("url", "#")
    m      = opp["margin_score"]
    c      = opp["competition_score"]
    comp   = opp["composite_score"]

    desc = opp["description"].replace("\n", "<br>")

    return f"""
    <tr>
      <td style="padding:16px 0;border-bottom:1px solid #eee;">
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td>
              <!-- Rank + source badge -->
              <span style="font-size:11px;font-weight:700;color:#aaa;">#{rank}</span>
              &nbsp;
              <span style="
                background:{color};color:#fff;font-size:10px;font-weight:700;
                padding:2px 7px;border-radius:20px;text-transform:uppercase;
                letter-spacing:.5px;">
                {source}
              </span>
              &nbsp;
              <span style="
                background:#f0f4ff;color:#3a5bef;font-size:11px;font-weight:700;
                padding:2px 8px;border-radius:20px;">
                Score&nbsp;{comp}
              </span>
            </td>
          </tr>
          <tr>
            <td style="padding-top:6px;">
              <a href="{url}" style="font-size:16px;font-weight:700;color:#1a1a2e;text-decoration:none;">
                {opp["title"]}
              </a>
            </td>
          </tr>
          <tr>
            <td style="padding-top:4px;font-size:13px;color:#555;line-height:1.5;">
              {desc}
            </td>
          </tr>
          <tr>
            <td style="padding-top:8px;">
              <!-- Margin score -->
              <span style="font-size:11px;color:#888;margin-right:6px;">
                Margin&nbsp;potential
              </span>
              {_score_bar(m, "#28a745")}
              <span style="font-size:11px;font-weight:700;color:#28a745;margin-left:4px;">{m}</span>
              &nbsp;&nbsp;
              <!-- Competition score -->
              <span style="font-size:11px;color:#888;margin-right:6px;">
                Low&nbsp;competition
              </span>
              {_score_bar(c, "#fd7e14")}
              <span style="font-size:11px;font-weight:700;color:#fd7e14;margin-left:4px;">{c}</span>
            </td>
          </tr>
        </table>
      </td>
    </tr>"""


def build_html(opportunities: List[Dict[str, Any]]) -> str:
    """Render the full HTML email body."""
    today       = date.today().strftime("%B %d, %Y")
    top_opps    = opportunities[:MAX_TOTAL]
    cards_html  = "\n".join(
        _opportunity_card(opp, i + 1) for i, opp in enumerate(top_opps)
    )
    count       = len(top_opps)

    # Source breakdown summary
    source_counts: Dict[str, int] = {}
    for opp in top_opps:
        source_counts[opp["source"]] = source_counts.get(opp["source"], 0) + 1
    summary_parts = [
        f'<span style="color:{_SOURCE_COLORS.get(s, _DEFAULT_COLOR)};font-weight:700;">'
        f"{s} ({n})</span>"
        for s, n in source_counts.items()
    ]
    source_summary = " &middot; ".join(summary_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Market Research Digest – {today}</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:24px 0;">
    <tr>
      <td align="center">
        <table width="640" cellpadding="0" cellspacing="0"
               style="background:#fff;border-radius:12px;overflow:hidden;
                      box-shadow:0 2px 8px rgba(0,0,0,.08);max-width:640px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);
                        padding:32px 36px;">
              <h1 style="margin:0;color:#fff;font-size:22px;font-weight:800;
                          letter-spacing:-.3px;">
                Daily Market Research Digest
              </h1>
              <p style="margin:6px 0 0;color:rgba(255,255,255,.65);font-size:13px;">
                {today} &middot; {count} high-margin, low-competition opportunities
              </p>
              <p style="margin:10px 0 0;font-size:12px;">{source_summary}</p>
            </td>
          </tr>

          <!-- Scoring legend -->
          <tr>
            <td style="padding:16px 36px;background:#f8faff;border-bottom:1px solid #eee;">
              <p style="margin:0;font-size:12px;color:#666;line-height:1.6;">
                <strong style="color:#28a745;">Margin potential</strong> — estimated profitability of the niche (B2B, compliance, premium markets score higher).&nbsp;
                <strong style="color:#fd7e14;">Low competition</strong> — freshness of the trend and scarcity of existing solutions.&nbsp;
                <strong style="color:#3a5bef;">Score</strong> — weighted composite (0-100).
              </p>
            </td>
          </tr>

          <!-- Opportunities -->
          <tr>
            <td style="padding:0 36px 24px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                {cards_html}
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 36px;background:#f8faff;border-top:1px solid #eee;">
              <p style="margin:0;font-size:11px;color:#aaa;text-align:center;">
                Generated by Market Research Tool &middot; Powered by Google Trends, Reddit, Product Hunt &amp; Hacker News
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_email(opportunities: List[Dict[str, Any]]) -> None:
    """Build and send the HTML digest email."""
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECIPIENT:
        logger.error(
            "Email credentials not configured. "
            "Set EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT in .env."
        )
        return

    today   = date.today().strftime("%B %d, %Y")
    subject = f"Market Research Digest – {today} ({len(opportunities[:MAX_TOTAL])} opportunities)"

    html_body  = build_html(opportunities)
    plain_body = _plain_text_fallback(opportunities)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECIPIENT
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body,  "html"))

    try:
        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        logger.info("Digest email sent to %s.", EMAIL_RECIPIENT)
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)
        raise


def _plain_text_fallback(opportunities: List[Dict[str, Any]]) -> str:
    lines = [
        f"MARKET RESEARCH DIGEST – {date.today().strftime('%B %d, %Y')}",
        "=" * 60,
        "",
    ]
    for i, opp in enumerate(opportunities[:MAX_TOTAL], 1):
        lines += [
            f"#{i} [{opp['source']}] Score: {opp['composite_score']}",
            f"   {opp['title']}",
            f"   Margin: {opp['margin_score']}  Competition: {opp['competition_score']}",
            f"   {opp['url']}",
            f"   {opp['description'][:200]}",
            "",
        ]
    return "\n".join(lines)
