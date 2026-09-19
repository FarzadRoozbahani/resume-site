#!/usr/bin/env python3
"""
Static site builder for feris.ir.

Reads:
  content/en/site.md, content/fa/site.md   -> the resume, one file per language
  content/en/blog/*.md, content/fa/blog/*.md -> blog posts (frontmatter + markdown body)

Writes (directly into the repo root, which is what GitHub Pages serves):
  /index.html            -> language redirect (browser-language based)
  /en/index.html         -> English resume
  /fa/index.html         -> Persian resume
  /en/blog/index.html    -> English blog listing
  /fa/blog/index.html    -> Persian blog listing
  /en/blog/<slug>/index.html  -> one per English post
  /fa/blog/<slug>/index.html  -> one per Persian post
  /sitemap.xml           -> every URL above

Run this after editing anything under content/, then commit + push.
No third-party packages required — stdlib only.
"""

import os
import re
import html
import glob
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE_URL = "https://feris.ir"

# ---------------------------------------------------------------- parsing --

def parse_sections(text):
    """Split a site.md file into ## sections, keyed by lowercase header text."""
    sections = {}
    current = None
    buf = []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+)", line)
        if m:
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = m.group(1).strip().lower()
            buf = []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def parse_key_values(block):
    """Parse 'Label: value' lines into an ordered dict of label(lower) -> value,
    plus preserve the original label text per key for display."""
    out = {}
    labels = {}
    for line in block.splitlines():
        m = re.match(r"^(.+?):\s+(.*)$", line.strip())
        if m:
            key = m.group(1).strip()
            out[key.lower()] = m.group(2).strip()
            labels[key.lower()] = key
    return out, labels


def split_subsections(block):
    """Split a section on ### sub-headers into [{header, body}]."""
    parts = re.split(r"^###\s+", block, flags=re.M)
    items = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        header = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        items.append({"header": header, "body": body})
    return items


def parse_frontmatter(text):
    """'---\nkey: value\n---\nbody' -> (dict, body)"""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.S)
    if not m:
        return {}, text
    fm_raw, body = m.group(1), m.group(2)
    fm = {}
    for line in fm_raw.splitlines():
        mm = re.match(r"^(\w+):\s*(.*)$", line.strip())
        if mm:
            fm[mm.group(1).strip().lower()] = mm.group(2).strip()
    return fm, body.strip()


# ------------------------------------------------------------- mini markdown --

def _inline(text):
    text = html.escape(text, quote=False)
    # protect inline code spans first so later bold/italic regex can't reach inside them
    code_spans = []
    def _stash(m):
        code_spans.append(m.group(1))
        return "\x00{}\x00".format(len(code_spans) - 1)
    text = re.sub(r"`([^`]+)`", _stash, text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: "<code>{}</code>".format(code_spans[int(m.group(1))]), text)
    return text


def markdown_to_html(body):
    blocks = re.split(r"\n\s*\n", body.strip())
    out = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        m = re.match(r"^(#{1,3})\s+(.*)", block)
        if m:
            level = len(m.group(1)) + 2  # start headings at h3 inside a post
            out.append("<h{0}>{1}</h{0}>".format(level, _inline(m.group(2).strip())))
            continue
        lines = block.splitlines()
        if all(re.match(r"^-\s+", l.strip()) for l in lines):
            items = "".join("<li>{}</li>".format(_inline(re.sub(r"^-\s+", "", l.strip()))) for l in lines)
            out.append("<ul>{}</ul>".format(items))
            continue
        if all(re.match(r"^\d+\.\s+", l.strip()) for l in lines):
            items = "".join("<li>{}</li>".format(_inline(re.sub(r"^\d+\.\s+", "", l.strip()))) for l in lines)
            out.append("<ol>{}</ol>".format(items))
            continue
        joined = " ".join(l.strip() for l in lines)
        out.append("<p>{}</p>".format(_inline(joined)))
    return "\n".join(out)


# ------------------------------------------------------------------- icons --

ICON_SVGS = {
    "mail": '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 6 12 13 2 6"/><rect x="2" y="4" width="20" height="16" rx="2"/></svg>',
    "pin": '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 6-9 12-9 12s-9-6-9-12a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    "phone": '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>',
    "music": '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
    "electronics": '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z"/></svg>',
    "gaming": '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="10" rx="3"/><circle cx="8" cy="12" r="1.5"/><circle cx="16" cy="12" r="1.5"/></svg>',
    "motorcycles": '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="5" cy="18" r="3"/><circle cx="19" cy="18" r="3"/><path d="M5 18l4-9h4l3 5h3M9 9l3 4"/></svg>',
    "gym": '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8v8M2 9v6M20 8v8M22 9v6"/><path d="M6 12h12" stroke-width="3"/></svg>',
    "default": '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/></svg>',
}

INTEREST_ALIASES = {
    "music": "music", "موسیقی": "music",
    "electronics": "electronics", "الکترونیک": "electronics",
    "gaming": "gaming", "گیم": "gaming",
    "motorcycles": "motorcycles", "موتورسواری": "motorcycles",
    "gym": "gym", "بدنسازی": "gym", "fitness": "gym",
}

def icon_for_interest(name):
    key = INTEREST_ALIASES.get(name.strip().lower(), None)
    return ICON_SVGS.get(key, ICON_SVGS["default"])

def icon_for_contact_label(label):
    l = label.lower()
    if re.search(r"email|mail|ایمیل", l):
        return "mail", True
    if re.search(r"phone|tel|تلفن|شماره", l):
        return "phone", False
    if re.search(r"location|address|موقعیت|آدرس", l):
        return "pin", False
    return "default", False


# --------------------------------------------------------------- CSS/shell --

CSS = r"""
:root{
  --bg: #070A12;
  --blob-cyan: #22D3EE;
  --blob-indigo: #6366F1;
  --blob-emerald: #34D399;
  --glass-fill: rgba(255,255,255,0.05);
  --glass-border: rgba(255,255,255,0.22);
  --text: #F3F6FB;
  --text-muted: #9AA7BD;
  --text-faint: #6B7690;
  --radius: 26px;
  --font-display: 'Sora', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --ease: cubic-bezier(.22,1,.36,1);
}
html[lang="fa"]{
  --font-display: 'Vazirmatn', sans-serif;
  --font-body: 'Vazirmatn', sans-serif;
  --font-mono: 'Vazirmatn', sans-serif;
}
*{box-sizing:border-box; margin:0; padding:0;}
html{scroll-behavior:smooth;}
body{ background: var(--bg); color: var(--text); font-family: var(--font-body); -webkit-font-smoothing: antialiased; min-height:100vh; overflow-x:hidden; position:relative; }
::selection{ background: var(--blob-cyan); color:#06121A; }
a{ color:inherit; text-decoration:none; }
ul{ list-style:none; }
img{ max-width:100%; display:block; }
:focus-visible{ outline: 2px solid var(--blob-cyan); outline-offset: 3px; border-radius: 6px; }

.aurora{ position: fixed; inset: 0; z-index: -2; overflow: hidden; background: var(--bg); }
.aurora span{ position:absolute; width: 60vmax; height: 60vmax; border-radius: 50%; filter: blur(70px); opacity: 0.45; mix-blend-mode: screen; will-change: transform; }
.aurora span:nth-child(1){ background: var(--blob-cyan); top: -18vmax; left: -14vmax; animation: float1 22s var(--ease) infinite alternate; }
.aurora span:nth-child(2){ background: var(--blob-indigo); bottom: -22vmax; right: -16vmax; animation: float2 26s var(--ease) infinite alternate; }
.aurora span:nth-child(3){ background: var(--blob-emerald); top: 35%; left: 45%; opacity: 0.28; animation: float3 30s var(--ease) infinite alternate; }
.aurora::after{ content:""; position:absolute; inset:0; background: radial-gradient(ellipse at 50% 0%, transparent 0%, var(--bg) 78%); }
@keyframes float1{ from{ transform: translate(0,0) scale(1);} to{ transform: translate(8vw, 10vh) scale(1.15);} }
@keyframes float2{ from{ transform: translate(0,0) scale(1);} to{ transform: translate(-6vw, -8vh) scale(1.1);} }
@keyframes float3{ from{ transform: translate(-50%,-50%) scale(0.9);} to{ transform: translate(-42%,-58%) scale(1.2);} }
@media (prefers-reduced-motion: reduce){ .aurora span{ animation: none !important; } html{ scroll-behavior:auto; } }

.glass{
  position: relative; background: var(--glass-fill); border: 1px solid var(--glass-border);
  backdrop-filter: blur(20px) saturate(150%); -webkit-backdrop-filter: blur(20px) saturate(150%);
  border-radius: var(--radius);
  box-shadow: 0 14px 44px rgba(0,0,0,0.42), inset 0 1px 0 rgba(255,255,255,0.45), inset 0 -1px 0 rgba(0,0,0,0.25), inset 0 0 0 1px rgba(255,255,255,0.04);
  isolation: isolate; overflow: hidden; contain: layout paint style;
}
.glass::before{ content:""; position:absolute; inset:0; background: linear-gradient(135deg, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.08) 22%, rgba(255,255,255,0) 45%); mix-blend-mode: overlay; pointer-events:none; z-index: 1; }
.glass::after{ content:""; position:absolute; inset:0; border-radius: inherit; padding: 1px; background: linear-gradient(160deg, rgba(255,255,255,0.55), rgba(255,255,255,0.02) 30%, rgba(255,255,255,0) 60%, rgba(255,255,255,0.12) 100%); -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude; pointer-events:none; z-index: 1; }
.glass > *{ position: relative; z-index: 2; }
.glass:active{ transform: scale(0.985); }

.glass-light{
  position: relative; background: linear-gradient(160deg, rgba(255,255,255,0.10), rgba(255,255,255,0.04));
  border: 1px solid var(--glass-border); border-radius: var(--radius);
  box-shadow: 0 6px 18px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.30), inset 0 -1px 0 rgba(0,0,0,0.18);
  contain: layout paint style;
}
.glass-light:active{ transform: scale(0.96); }

.wrap{ max-width: 760px; margin: 0 auto; padding: 0 18px 90px; }
.topbar{ position: sticky; top: 0; z-index: 40; display:flex; align-items:center; justify-content:space-between; gap:10px; padding: 16px 18px; max-width: 760px; margin: 0 auto; }
.brand{ font-family: var(--font-display); font-weight: 700; font-size: 14.5px; letter-spacing: 0.02em; padding: 10px 22px; border-radius: 999px; }
.topbar nav{ display:flex; gap:8px; }
.topbar nav a{ font-family: var(--font-mono); font-size: 12px; letter-spacing:0.04em; padding: 9px 14px; border-radius: 999px; color: var(--text-muted); }
.topbar nav a:hover, .topbar nav a.active{ color: var(--text); }

.hero{ padding: 26px 0 8px; display:flex; flex-direction: column; align-items:center; text-align:center; }
.avatar-ring{ width: 132px; height: 132px; border-radius: 50%; padding: 3px; margin-bottom: 22px; background: rgba(255,255,255,0.14); box-shadow: inset 0 1px 2px rgba(255,255,255,0.6), inset 0 -2px 6px rgba(0,0,0,0.3), 0 10px 30px rgba(34,211,238,0.18); border: 1px solid rgba(255,255,255,0.25); }
.avatar-ring .inner{ width:100%; height:100%; border-radius: 50%; overflow: hidden; background: var(--bg); }
.avatar-ring img{ width:100%; height:100%; object-fit: cover; object-position: center 14%; }
.eyebrow{ font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--blob-cyan); padding: 7px 16px; border-radius: 999px; margin-bottom: 18px; display:inline-block; }
h1{ font-family: var(--font-display); font-weight: 800; font-size: clamp(30px, 8vw, 44px); line-height: 1.15; letter-spacing: -0.01em; }
.tagline{ margin-top: 12px; font-size: 16px; line-height: 1.7; color: var(--text-muted); max-width: 460px; }
.location{ margin-top: 14px; font-family: var(--font-mono); font-size: 12.5px; color: var(--text-faint); display:flex; align-items:center; gap:6px; }
.dot{ width:6px; height:6px; border-radius:50%; background: var(--blob-emerald); box-shadow: 0 0 8px var(--blob-emerald); }
.cta-row{ margin-top: 28px; display:flex; gap:10px; flex-wrap: wrap; justify-content:center; }
.btn{ font-family: var(--font-body); font-weight: 600; font-size: 14.5px; padding: 13px 26px; border-radius: 999px; display:inline-flex; align-items:center; gap:8px; transition: transform .3s var(--ease); }
.btn:active{ transform: scale(0.96); }
.btn-primary{ background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(230,238,248,0.9)); color: #06121A; border: none; box-shadow: 0 10px 28px rgba(34,211,238,0.25), inset 0 1px 0 rgba(255,255,255,1); }

section{ margin-top: 46px; }
.section-head{ display:flex; align-items:baseline; gap: 10px; margin-bottom: 18px; padding: 0 4px; }
.section-head .num{ font-family: var(--font-mono); font-size: 12px; color: var(--text-faint); }
.section-head h2{ font-family: var(--font-display); font-weight: 700; font-size: 22px; }
.card{ padding: 24px; margin-bottom: 14px; }
.card p, .card .muted{ color: var(--text-muted); line-height: 1.85; font-size: 14.5px; }

.timeline{ position:relative; }
.timeline::before{ content:""; position:absolute; top: 8px; bottom: 8px; inset-inline-start: 27px; width: 1px; background: linear-gradient(var(--blob-cyan), var(--blob-indigo), transparent); opacity: 0.4; }
.job{ position: relative; padding: 20px 22px; padding-inline-start: 58px; margin-bottom: 12px; }
.job::before{ content:""; position:absolute; inset-inline-start: 22px; top: 26px; width: 11px; height: 11px; border-radius: 50%; background: var(--bg); border: 2px solid var(--blob-cyan); box-shadow: 0 0 10px rgba(34,211,238,0.6); z-index: 2; }
.job .role{ font-family: var(--font-display); font-weight: 700; font-size: 16px; }
.job .org{ color: var(--blob-cyan); font-size: 13.5px; font-weight: 600; margin-top: 2px; }
.job .period{ font-family: var(--font-mono); font-size: 11.5px; color: var(--text-faint); margin-top: 4px; letter-spacing: 0.03em; }
.job .desc{ margin-top: 10px; }

.skill-group{ margin-bottom: 18px; }
.skill-group:last-child{ margin-bottom: 0; }
.skill-group h3{ font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-faint); margin-bottom: 10px; padding: 0 4px; }
.chips{ display:flex; flex-wrap:wrap; gap:8px; }
.chip{ font-size: 13px; font-weight: 500; padding: 9px 15px; border-radius: 999px; color: var(--text); transition: transform .25s var(--ease), border-color .25s var(--ease); }
.chip:hover{ transform: translateY(-2px); border-color: var(--blob-cyan); }

.edu-title{ font-family: var(--font-display); font-weight: 700; font-size: 16px; }
.edu-sub{ color: var(--blob-emerald); font-size: 13.5px; font-weight: 600; margin-top: 4px; }
.langs{ display:flex; gap: 12px; flex-wrap: wrap; }
.lang-card{ flex:1; min-width: 140px; padding: 18px; text-align:center; }
.lang-card .name{ font-family: var(--font-display); font-weight: 700; font-size: 15px; }
.lang-card .level{ font-family: var(--font-mono); font-size: 11.5px; color: var(--blob-cyan); margin-top: 6px; letter-spacing:0.05em; }

.interests{ display:flex; gap:10px; flex-wrap:wrap; }
.interest{ display:flex; align-items:center; gap:8px; padding: 11px 17px; font-size: 13.5px; font-weight: 500; }
.interest svg{ width:16px; height:16px; stroke: var(--blob-cyan); flex-shrink:0; }

.contact-grid{ display:flex; flex-direction:column; gap:10px; }
.contact-row{ display:flex; align-items:center; gap:14px; padding: 18px; transition: border-color .25s var(--ease); }
.contact-row:hover{ border-color: var(--blob-cyan); }
.contact-row .icon{ width: 40px; height: 40px; border-radius: 13px; display:flex; align-items:center; justify-content:center; background: linear-gradient(135deg, rgba(34,211,238,0.18), rgba(99,102,241,0.18)); flex-shrink:0; }
.contact-row .icon svg{ width:19px; height:19px; stroke: var(--blob-cyan); }
.contact-row .label{ font-family: var(--font-mono); font-size: 10.5px; color: var(--text-faint); text-transform:uppercase; letter-spacing:0.06em; }
.contact-row .value{ font-size: 15px; font-weight: 600; margin-top: 2px; word-break: break-all; }

footer{ text-align:center; padding: 30px 20px 10px; color: var(--text-faint); font-family: var(--font-mono); font-size: 11.5px; }

/* ---- blog ---- */
.post-card{ padding: 22px; margin-bottom: 14px; display:block; }
.post-card .post-date{ font-family: var(--font-mono); font-size: 11.5px; color: var(--text-faint); letter-spacing:0.03em; }
.post-card h3{ font-family: var(--font-display); font-weight: 700; font-size: 18px; margin-top: 8px; }
.post-card .excerpt{ margin-top: 8px; color: var(--text-muted); font-size: 14px; line-height: 1.7; }
.post-card .readmore{ margin-top: 12px; display:inline-block; font-family: var(--font-mono); font-size: 12px; color: var(--blob-cyan); }

article.post{ padding: 28px; }
article.post .post-date{ font-family: var(--font-mono); font-size: 12px; color: var(--text-faint); }
article.post h1{ margin-top: 10px; font-size: clamp(26px, 6vw, 36px); }
article.post .body{ margin-top: 22px; color: var(--text-muted); line-height: 1.9; font-size: 15.5px; }
article.post .body h3, article.post .body h4, article.post .body h5{ font-family: var(--font-display); color: var(--text); margin: 26px 0 10px; }
article.post .body p{ margin-bottom: 16px; }
article.post .body ul{ margin: 0 0 16px; padding-inline-start: 22px; list-style: disc; }
article.post .body ol{ margin: 0 0 16px; padding-inline-start: 22px; list-style: decimal; }
article.post .body li{ margin-bottom: 6px; }
article.post .body a{ color: var(--blob-cyan); text-decoration: underline; }
article.post .body code{ background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 6px; font-family: var(--font-mono); font-size: 0.9em; }
.back-link{ display:inline-flex; align-items:center; gap:6px; font-family: var(--font-mono); font-size: 12.5px; color: var(--text-faint); margin-bottom: 18px; }
.back-link:hover{ color: var(--text); }

@media (min-width: 620px){ .hero{ padding-top: 42px; } }
"""

FONT_LINK = {
    "en": '<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">',
    "fa": '<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap" rel="stylesheet">',
}

STRINGS = {
    "en": {
        "about": "About", "experience": "Experience", "skills": "Skills",
        "softskills": "Soft Skills", "education": "Education", "languages": "Languages",
        "interests": "Beyond work", "contact": "Get in touch", "email_btn": "Email me",
        "blog_nav": "Blog", "resume_nav": "Resume", "blog_title": "Blog",
        "blog_index_title": "Blog — {name}", "back_to_blog": "← Back to blog",
        "site_desc": "Farzad Roozbahani is an SEO specialist and developer based in Tehran, working with clients including RugMaster (Australia) on technical SEO, keyword strategy, and WordPress development.",
    },
    "fa": {
        "about": "درباره من", "experience": "سوابق کاری", "skills": "مهارت‌ها",
        "softskills": "مهارت‌های نرم", "education": "تحصیلات", "languages": "زبان‌ها",
        "interests": "بیرون از کار", "contact": "در تماس باشیم", "email_btn": "ایمیل بزن",
        "blog_nav": "بلاگ", "resume_nav": "رزومه", "blog_title": "بلاگ",
        "blog_index_title": "بلاگ — {name}", "back_to_blog": "← بازگشت به بلاگ",
        "site_desc": "فرزاد روزبهانی متخصص سئو و توسعه‌دهنده مستقر در تهران است که با مشتریانی از جمله رگ‌مستر (استرالیا) روی سئوی فنی، استراتژی کلمات کلیدی و توسعه‌ی وردپرس همکاری می‌کند.",
    },
}

OTHER_LANG = {"en": "fa", "fa": "en"}


def page_shell(lang, title, description, canonical_path, body, extra_head="", nav_active="resume"):
    other = OTHER_LANG[lang]
    dir_attr = "rtl" if lang == "fa" else "ltr"
    s = STRINGS[lang]
    canonical = SITE_URL + canonical_path
    alt_en = SITE_URL + ("/en/" if canonical_path.startswith("/en") else "/en" + canonical_path[3:] if canonical_path.startswith("/fa") else "/en/")
    alt_fa = SITE_URL + ("/fa/" if canonical_path.startswith("/fa") else "/fa" + canonical_path[3:] if canonical_path.startswith("/en") else "/fa/")

    nav_html = '<nav><a href="/{o}/" title="{label}">{code}</a><a href="/{l}/blog/" class="{blogcls}">{blog}</a></nav>'.format(
        o=other, label=("English" if other == "en" else "فارسی"), code=other.upper(),
        l=lang, blogcls=("active" if nav_active == "blog" else ""), blog=s["blog_nav"]
    )

    return """<!DOCTYPE html>
<html lang="{lang}" dir="{dir_attr}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="theme-color" content="#070A12">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{alt_en}">
<link rel="alternate" hreflang="fa" href="{alt_fa}">
<link rel="alternate" hreflang="x-default" href="{site}/">
<link rel="sitemap" type="application/xml" href="/sitemap.xml">

<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:image" content="{site}/assets/farzad.png">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="{locale}">
<meta name="twitter:card" content="summary">

<link rel="icon" href="data:,">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
{font_link}
{extra_head}
<style>{css}</style>
</head>
<body>
<div class="aurora" aria-hidden="true"><span></span><span></span><span></span></div>
<div class="topbar">
  <a href="/{lang}/" class="brand glass-light">{name}</a>
  {nav}
</div>
{body}
</body>
</html>""".format(
        lang=lang, dir_attr=dir_attr, title=html.escape(title), description=html.escape(description),
        canonical=canonical, alt_en=alt_en, alt_fa=alt_fa, site=SITE_URL,
        locale=("fa_IR" if lang == "fa" else "en_US"), font_link=FONT_LINK[lang],
        extra_head=extra_head, css=CSS, name="Farzad Roozbahani", nav=nav_html, body=body,
    )


# ------------------------------------------------------------- resume page --

def build_person_schema(lang, sections, hero):
    experiences = split_subsections(sections.get("experience", ""))
    current_job = next((e for e in experiences if re.search(r"now|اکنون", e["header"], re.I)), experiences[0] if experiences else None)
    org = ""
    if current_job:
        parts = [p.strip() for p in current_job["header"].split("|")]
        org = parts[1] if len(parts) > 1 else ""

    edu_items = split_subsections(sections.get("education", ""))
    alumni = edu_items[0]["header"].split("|")[0].strip() if edu_items else ""

    knows_about = []
    for g in split_subsections(sections.get("skills", "")):
        for s in [x.strip() for x in g["body"].split(",") if x.strip()]:
            if s not in knows_about:
                knows_about.append(s)

    contact_kv, contact_labels = parse_key_values(sections.get("contact", ""))
    loc_raw = contact_kv.get("location") or contact_kv.get("موقعیت مکانی") or hero.get("location", "")
    locality = loc_raw.split(",")[0].strip() if loc_raw else ""

    schema = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": hero.get("name", ""),
        "jobTitle": hero.get("eyebrow", ""),
        "description": sections.get("about", "").strip(),
        "url": "{}/{}/".format(SITE_URL, lang),
        "image": "{}/assets/farzad.png".format(SITE_URL),
        "email": "mailto:" + hero["email"] if hero.get("email") else None,
        "address": {"@type": "PostalAddress", "addressLocality": locality, "addressCountry": "IR"} if locality else None,
        "worksFor": {"@type": "Organization", "name": org} if org else None,
        "alumniOf": {"@type": "EducationalOrganization", "name": alumni} if alumni else None,
        "knowsLanguage": ["fa", "en"],
        "knowsAbout": knows_about or None,
        "sameAs": ["{}/{}/".format(SITE_URL, lang)],
    }
    schema = {k: v for k, v in schema.items() if v is not None}
    import json
    return json.dumps(schema, indent=2, ensure_ascii=False)


def render_resume(lang, sections):
    s = STRINGS[lang]
    hero, _ = parse_key_values(sections.get("hero", ""))

    body = []
    body.append('<main class="wrap">')
    body.append('<section class="hero">')
    body.append('<div class="avatar-ring"><div class="inner"><img src="/assets/farzad.png" alt="{}" width="132" height="132"></div></div>'.format(html.escape(hero.get("name", ""))))
    body.append('<span class="eyebrow glass-light">{}</span>'.format(html.escape(hero.get("eyebrow", ""))))
    body.append('<h1>{}</h1>'.format(html.escape(hero.get("name", ""))))
    body.append('<p class="tagline">{}</p>'.format(html.escape(hero.get("tagline", ""))))
    body.append('<div class="location"><span class="dot"></span><span>{}</span></div>'.format(html.escape(hero.get("location", ""))))
    if hero.get("email"):
        body.append('<div class="cta-row"><a class="btn btn-primary" href="mailto:{0}">{1}</a></div>'.format(hero["email"], s["email_btn"]))
    body.append('</section>')

    body.append('<section id="about"><div class="section-head"><span class="num">01</span><h2>{}</h2></div>'.format(s["about"]))
    body.append('<div class="card glass"><p>{}</p></div></section>'.format(html.escape(sections.get("about", "").strip())))

    body.append('<section id="experience"><div class="section-head"><span class="num">02</span><h2>{}</h2></div><div class="timeline">'.format(s["experience"]))
    for item in split_subsections(sections.get("experience", "")):
        parts = [p.strip() for p in item["header"].split("|")]
        role, org, period = (parts + ["", "", ""])[:3]
        body.append('<div class="job glass"><div class="role">{}</div><div class="org">{}</div><div class="period">{}</div><p class="desc muted">{}</p></div>'.format(
            html.escape(role), html.escape(org), html.escape(period), html.escape(item["body"])))
    body.append('</div></section>')

    body.append('<section id="skills"><div class="section-head"><span class="num">03</span><h2>{}</h2></div><div class="card glass">'.format(s["skills"]))
    for g in split_subsections(sections.get("skills", "")):
        body.append('<div class="skill-group"><h3>{}</h3><div class="chips">'.format(html.escape(g["header"])))
        for name in [x.strip() for x in g["body"].split(",") if x.strip()]:
            body.append('<span class="chip glass-light">{}</span>'.format(html.escape(name)))
        body.append('</div></div>')
    body.append('</div></section>')

    soft = sections.get("soft skills", "")
    if soft.strip():
        body.append('<section id="softskills"><div class="section-head"><span class="num">04</span><h2>{}</h2></div><div class="card glass"><div class="chips">'.format(s["softskills"]))
        for name in [x.strip() for x in soft.split(",") if x.strip()]:
            body.append('<span class="chip glass-light">{}</span>'.format(html.escape(name)))
        body.append('</div></div></section>')

    body.append('<section id="education"><div class="section-head"><span class="num">05</span><h2>{}</h2></div>'.format(s["education"]))
    for item in split_subsections(sections.get("education", "")):
        parts = [p.strip() for p in item["header"].split("|")]
        school, degree = (parts + ["", ""])[:2]
        body.append('<div class="card glass"><div class="edu-title">{}</div><div class="edu-sub">{}</div><p style="margin-top:10px">{}</p></div>'.format(
            html.escape(school), html.escape(degree), html.escape(item["body"])))
    body.append('</section>')

    body.append('<section id="languages"><div class="section-head"><span class="num">06</span><h2>{}</h2></div><div class="langs">'.format(s["languages"]))
    lang_kv, lang_labels = parse_key_values(sections.get("languages", ""))
    for key, value in lang_kv.items():
        body.append('<div class="lang-card glass"><div class="name">{}</div><div class="level">{}</div></div>'.format(
            html.escape(lang_labels[key]), html.escape(value)))
    body.append('</div></section>')

    body.append('<section id="interests"><div class="section-head"><span class="num">07</span><h2>{}</h2></div><div class="interests">'.format(s["interests"]))
    for name in [x.strip() for x in sections.get("interests", "").split(",") if x.strip()]:
        body.append('<span class="interest glass-light">{}<span>{}</span></span>'.format(icon_for_interest(name), html.escape(name)))
    body.append('</div></section>')

    body.append('<section id="contact"><div class="section-head"><span class="num">08</span><h2>{}</h2></div><div class="contact-grid">'.format(s["contact"]))
    contact_kv, contact_labels = parse_key_values(sections.get("contact", ""))
    for key, value in contact_kv.items():
        icon_key, is_email = icon_for_contact_label(contact_labels[key])
        tag = "a" if is_email else "div"
        href = ' href="mailto:{}"'.format(value) if is_email else ""
        body.append('<{tag} class="contact-row glass"{href}><span class="icon">{icon}</span><div><div class="label">{label}</div><div class="value">{value}</div></div></{tag}>'.format(
            tag=tag, href=href, icon=ICON_SVGS[icon_key], label=html.escape(contact_labels[key]), value=html.escape(value)))
    body.append('</div></section>')

    year = date.today().year
    body.append('<footer>&copy; {} {}</footer>'.format(year, html.escape(hero.get("name", ""))))
    body.append('</main>')

    schema_json = build_person_schema(lang, sections, hero)
    extra_head = '<script type="application/ld+json">\n{}\n</script>'.format(schema_json)

    title = "{} | {}".format(hero.get("name", ""), hero.get("eyebrow", ""))
    return page_shell(lang, title, STRINGS[lang]["site_desc"], "/{}/".format(lang), "\n".join(body), extra_head, nav_active="resume")


# --------------------------------------------------------------------- blog --

def load_posts(lang):
    posts = []
    for path in sorted(glob.glob(os.path.join(ROOT, "content", lang, "blog", "*.md"))):
        slug = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        fm, body = parse_frontmatter(raw)
        posts.append({
            "slug": slug,
            "title": fm.get("title", slug),
            "date": fm.get("date", ""),
            "excerpt": fm.get("excerpt", ""),
            "body_html": markdown_to_html(body),
        })
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


def render_blog_index(lang, posts, hero_name):
    s = STRINGS[lang]
    body = ['<main class="wrap">', '<section style="padding-top:26px">',
            '<div class="section-head"><h2 style="font-size:28px">{}</h2></div>'.format(s["blog_title"])]
    if not posts:
        body.append('<div class="card glass"><p class="muted">{}</p></div>'.format(
            "No posts yet." if lang == "en" else "هنوز پستی منتشر نشده."))
    for p in posts:
        body.append(
            '<a class="post-card glass" href="/{lang}/blog/{slug}/">'
            '<div class="post-date">{date}</div><h3>{title}</h3>'
            '<p class="excerpt">{excerpt}</p>'
            '<span class="readmore">{more}</span></a>'.format(
                lang=lang, slug=p["slug"], date=html.escape(p["date"]),
                title=html.escape(p["title"]), excerpt=html.escape(p["excerpt"]),
                more=("Read more →" if lang == "en" else "ادامه مطلب ←"))
        )
    body.append('</section></main>')

    title = s["blog_index_title"].format(name=hero_name)
    return page_shell(lang, title, s["site_desc"], "/{}/blog/".format(lang), "\n".join(body), nav_active="blog")


def render_blog_post(lang, post, hero_name):
    s = STRINGS[lang]
    body = [
        '<main class="wrap">',
        '<section style="padding-top:26px">',
        '<a class="back-link" href="/{}/blog/">{}</a>'.format(lang, s["back_to_blog"]),
        '<article class="post glass">',
        '<div class="post-date">{}</div>'.format(html.escape(post["date"])),
        '<h1>{}</h1>'.format(html.escape(post["title"])),
        '<div class="body">{}</div>'.format(post["body_html"]),
        '</article>',
        '</section>',
        '</main>',
    ]
    title = "{} | {}".format(post["title"], hero_name)
    canonical = "/{}/blog/{}/".format(lang, post["slug"])
    return page_shell(lang, title, post["excerpt"] or s["site_desc"], canonical, "\n".join(body), nav_active="blog")


# --------------------------------------------------------------- redirect --

def render_root_redirect():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Farzad Roozbahani</title>
<link rel="canonical" href="{site}/">
<link rel="alternate" hreflang="en" href="{site}/en/">
<link rel="alternate" hreflang="fa" href="{site}/fa/">
<link rel="alternate" hreflang="x-default" href="{site}/">
<meta name="robots" content="noindex, follow">
<style>
  body{{ background:#070A12; color:#F3F6FB; font-family: -apple-system, sans-serif; min-height:100vh;
        display:flex; align-items:center; justify-content:center; text-align:center; }}
  a{{ color:#22D3EE; text-decoration:none; margin: 0 10px; font-weight:600; }}
</style>
<script>
  var lang = (navigator.language || navigator.userLanguage || 'en').toLowerCase();
  var target = lang.indexOf('fa') === 0 ? '/fa/' : '/en/';
  location.replace(target);
</script>
</head>
<body>
  <noscript>
    <p>Choose your language / زبان خود را انتخاب کنید:</p>
    <p><a href="/en/">English</a> · <a href="/fa/">فارسی</a></p>
  </noscript>
  <p style="display:none">Redirecting… <a href="/en/">English</a> · <a href="/fa/">فارسی</a></p>
</body>
</html>""".format(site=SITE_URL)


# -------------------------------------------------------------- sitemap --

def build_sitemap(urls):
    entries = "\n".join(
        '  <url>\n    <loc>{}</loc>\n    <lastmod>{}</lastmod>\n    <changefreq>{}</changefreq>\n    <priority>{}</priority>\n  </url>'.format(
            u["loc"], u["lastmod"], u["changefreq"], u["priority"]
        ) for u in urls
    )
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{}\n</urlset>\n'.format(entries)


# ----------------------------------------------------------------- main --

def write(path, content):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", path)


def main():
    today = date.today().isoformat()
    sitemap_urls = [{"loc": SITE_URL + "/", "lastmod": today, "changefreq": "yearly", "priority": "0.5"}]

    for lang in ("en", "fa"):
        with open(os.path.join(ROOT, "content", lang, "site.md"), encoding="utf-8") as f:
            sections = parse_sections(f.read())
        hero, _ = parse_key_values(sections.get("hero", ""))

        write("{}/index.html".format(lang), render_resume(lang, sections))
        sitemap_urls.append({"loc": "{}/{}/".format(SITE_URL, lang), "lastmod": today, "changefreq": "monthly", "priority": "1.0"})

        posts = load_posts(lang)
        write("{}/blog/index.html".format(lang), render_blog_index(lang, posts, hero.get("name", "")))
        sitemap_urls.append({"loc": "{}/{}/blog/".format(SITE_URL, lang), "lastmod": today, "changefreq": "weekly", "priority": "0.8"})

        for post in posts:
            write("{}/blog/{}/index.html".format(lang, post["slug"]), render_blog_post(lang, post, hero.get("name", "")))
            sitemap_urls.append({"loc": "{}/{}/blog/{}/".format(SITE_URL, lang, post["slug"]), "lastmod": post["date"] or today, "changefreq": "monthly", "priority": "0.6"})

    write("index.html", render_root_redirect())
    write("sitemap.xml", build_sitemap(sitemap_urls))

    # keep Jekyll out of the way — this is a hand-built static site
    write(".nojekyll", "")

    print("\nBuild complete: {} pages + sitemap.".format(len(sitemap_urls)))


if __name__ == "__main__":
    main()
