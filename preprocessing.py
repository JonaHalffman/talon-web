"""
Pre-processing functions for email HTML before quotation extraction.
Each function should accept HTML string and return modified HTML string.
"""

import re
from typing import Optional, Tuple


def detect_email_client(html: str) -> str:
    """
    Detect the email client format from HTML.
    Returns: o365, outlook_desktop, gmail, apple_mail, yahoo, word_generated, unknown
    """
    html_lower = html.lower()
    
    if 'divrplyfwdmsg' in html_lower or 'rplyedtprsngmsg' in html_lower:
        return "o365"
    elif 'border-top:solid' in html_lower or 'border-top:double' in html_lower:
        return "outlook_desktop"
    elif 'gmail_quote' in html_lower:
        return "gmail"
    elif 'type="cite"' in html_lower:
        return "apple_mail"
    elif '<blockquote' in html_lower:
        return "yahoo"
    elif 'microsoft word' in html_lower or 'generator" content="microsoft word' in html_lower:
        return "word_generated"
    
    return "unknown"


def remove_o365_reply_div(html: str) -> str:
    """
    Remove O365 reply marker div and following quoted content div.
    Talon's cut_microsoft_quote() finds the marker but misses sibling divs.
    Handles multiple O365 nested div structures.
    """
    patterns = [
        r'<div[^>]*id="divRplyFwdMsg"[^>]*>.*?</div>\s*<div[^>]*>',
        r'<div[^>]*id="divRplyFwdMsg"[^>]*>.*?</div>\s*<div[^>]*>\s*<div[^>]*>',
        r'<div[^>]*class="RplyEdtPrsngMsg"[^>]*>.*?</div>\s*<div[^>]*>',
        r'<div[^>]*class="RplyEdtPrsngMsg"[^>]*>.*?</div>\s*<div[^>]*>\s*<div[^>]*>',
    ]
    
    for pattern in patterns:
        html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)
    
    return html


def remove_o365_forward_div(html: str) -> str:
    """
    Remove O365 forward marker divs.
    """
    patterns = [
        r'<div[^>]*id="divRplyFwdMsg"[^>]*>.*?forwarded.*?</div>',
    ]
    
    for pattern in patterns:
        html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)
    
    return html


def remove_outlook_web_reply_marker(html: str) -> str:
    """Remove Outlook Web (O365) reply header divs."""
    patterns = [
        r'<div[^>]*class="RplyEdtPrsngMsg"[^>]*>.*?</div>',
        r'<div[^>]*id="divRplyFwdMsg"[^>]*>.*?</div>',
    ]
    
    for pattern in patterns:
        html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)
    
    return html


def remove_outlook_desktop_quoted_content(html: str) -> str:
    """
    Remove Outlook Desktop quoted content.
    Finds 'border-top:solid' marker and removes everything after it.
    Handles various Outlook quote header formats.
    """
    patterns = [
        r'<div[^>]*style="[^"]*border-top:solid[^"]*"[^>]*>.*',
        r'<div[^>]*style="border:none;\s*border-top:solid[^"]*"[^>]*>.*',
    ]
    
    for pattern in patterns:
        html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)
    
    return html


def remove_gmail_quote_marker(html: str) -> str:
    """
    Remove Gmail quoted content markers.
    Gmail uses class="gmail_quote" for quoted content.
    """
    patterns = [
        r'<div[^>]*class="gmail_quote"[^>]*>.*',
    ]
    
    for pattern in patterns:
        html = re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)
    
    return html


def remove_apple_mail_quote(html: str) -> str:
    """
    Remove Apple Mail quoted content.
    Apple Mail uses type="cite" in blockquotes.
    """
    return html


def remove_yahoo_quote(html: str) -> str:
    """
    Remove Yahoo quoted content.
    Yahoo uses blockquote without specific class.
    """
    return html


def normalize_blockquotes(html: str) -> str:
    """
    Normalize various blockquote formats for better talon detection.
    """
    html = re.sub(r'<blockquote[^>]*type="cite"[^>]*>', '<blockquote class="apple_quote">', html, flags=re.IGNORECASE)
    html = re.sub(r'<blockquote[^>]*class="gmail_quote"[^>]*>', '<blockquote class="gmail_quote">', html, flags=re.IGNORECASE)
    
    return html


def extract_quoted_content(html: str, format_type: str) -> Tuple[str, str]:
    """
    Extract quoted content from HTML before removal.
    Returns: (cleaned_html, quoted_html)
    """
    quoted_html = ""
    
    if format_type == "o365":
        match = re.search(
            r'<div[^>]*id="divRplyFwdMsg"[^>]*>.*?</div>\s*(<div[^>]*>.*)',
            html, flags=re.DOTALL | re.IGNORECASE
        )
        if match:
            quoted_html = match.group(1)
            html = html[:match.start()]
    
    elif format_type == "outlook_desktop":
        match = re.search(
            r'(<div[^>]*style="[^"]*border-top:solid[^"]*"[^>]*>.*)',
            html, flags=re.DOTALL | re.IGNORECASE
        )
        if match:
            quoted_html = match.group(1)
            html = html[:match.start()]
    
    elif format_type == "gmail" or format_type == "yahoo":
        match = re.search(
            r'(<blockquote[^>]*>.*?</blockquote>)',
            html, flags=re.DOTALL | re.IGNORECASE
        )
        if match:
            quoted_html = match.group(1)
            html = html[:match.start()] + html[match.end():]
    
    html = fix_html_structure(html)
    
    return html, quoted_html


def fix_html_structure(html: str) -> str:
    """
    Fix common HTML structure issues that can break parsing.
    - Closes unclosed div tags
    - Ensures proper HTML document structure
    """
    if not html:
        return html
    
    open_divs = html.count('<div') - html.count('</div')
    open_spans = html.count('<span') - html.count('</span')
    open_ps = html.count('<p') - html.count('</p')
    
    for _ in range(open_divs):
        html += '</div>'
    for _ in range(open_spans):
        html += '</span>'
    for _ in range(open_ps):
        html += '</p>'
    
    if '</body>' not in html.lower() and '</html>' not in html.lower():
        html += '</body></html>'
    elif '</body>' not in html.lower():
        html = html.replace('</html>', '</body></html>')
    
    return html


def detect_reply_forward(html: str) -> dict:
    """
    Detect if email is a reply or forward from subject/headers.
    Returns: {is_reply: bool, is_forward: bool}
    """
    is_reply = False
    is_forward = False
    
    subject_match = re.search(r'<b[^>]*>Onderwerp:|Subject:</b>\s*([^<]+)', html, re.IGNORECASE)
    if subject_match and subject_match.group(1):
        subject = subject_match.group(1).lower()
        if subject.startswith('re:'):
            is_reply = True
        elif subject.startswith('fw:') or subject.startswith('fw:'):
            is_forward = True
    
    return {"is_reply": is_reply, "is_forward": is_forward}


def clean_subject(subject: str) -> dict:
    """
    Clean subject line by removing reply/forward prefixes.
    Returns: {original: str, clean: str, prefix: str, is_reply: bool, is_forward: bool}
    
    Handles: RE:, RE[n]:, FW:, FWD:, Fwd:, Ré:, AW:, WG:, etc.
    """
    result = {
        "original": subject,
        "clean": subject,
        "prefix": "",
        "is_reply": False,
        "is_forward": False,
    }
    
    if not subject:
        return result
    
    subject_clean = subject.strip()
    
    reply_patterns = [
        r'^(re[\[\s\d:\]]*):\s*',
        r'^(ré[\[\s\d:\]]*):\s*',
        r'^(aw[\[\s\d:\]]*):\s*',  # Antwoord (Dutch)
        r'^(antw[\[\s\d:\]]*):\s*',
        r'^(antwort[\[\s\d:\]]*):\s*',  # German
        r'^(odp[\[\s\d:\]]*):\s*',  # Polish
        r'^(sv[\[\s\d:\]]*):\s*',  # Swedish
    ]
    
    forward_patterns = [
        r'^(fw[\[\s\d:\]]*):\s*',
        r'^(fwd[\[\s\d:\]]*):\s*',
        r'^(vs[\[\s\d:\]]*):\s*',  # Dutch
        r'^( Weiterleitung)',  # German
    ]
    
    for pattern in reply_patterns:
        match = re.match(pattern, subject_clean, re.IGNORECASE)
        if match:
            result["prefix"] = match.group(1)
            result["clean"] = subject_clean[match.end():].strip()
            result["is_reply"] = True
            break
    
    if not result["is_reply"]:
        for pattern in forward_patterns:
            match = re.match(pattern, subject_clean, re.IGNORECASE)
            if match:
                result["prefix"] = match.group(1)
                result["clean"] = subject_clean[match.end():].strip()
                result["is_forward"] = True
                break
    
    return result


def detect_subject_change(html: str, original_subject: str = None) -> dict:
    """
    Detect if subject has changed in a thread.
    Compares current subject with quoted/previous subject headers.
    
    Returns: {
        "subject_changed": bool,
        "current_subject": str,
        "previous_subject": str,
        "thread_break": bool
    }
    
    thread_break: True if subject changed significantly (new conversation)
    """
    result = {
        "subject_changed": False,
        "current_subject": "",
        "previous_subject": "",
        "thread_break": False,
    }
    
    current_match = re.search(r'<b[^>]*>Onderwerp:</b>\s*([^<]+)', html, re.IGNORECASE)
    if not current_match:
        current_match = re.search(r'<b[^>]*>Subject:</b>\s*([^<]+)', html, re.IGNORECASE)
    if current_match and current_match.group(1):
        result["current_subject"] = current_match.group(1).strip()
    
    if original_subject:
        result["previous_subject"] = original_subject
        if result["current_subject"] and result["previous_subject"]:
            current_clean = clean_subject(result["current_subject"])["clean"]
            prev_clean = clean_subject(result["previous_subject"])["clean"]
            
            if current_clean.lower() != prev_clean.lower():
                result["subject_changed"] = True
                result["thread_break"] = True
        
        return result
    
    header_subjects = re.findall(r'<b[^>]*>Onderwerp:</b>\s*([^<]+)', html, re.IGNORECASE)
    header_subjects.extend(re.findall(r'<b[^>]*>Subject:</b>\s*([^<]+)', html, re.IGNORECASE))
    
    if len(header_subjects) > 1:
        result["previous_subject"] = header_subjects[-1].strip()
        
        current_clean = clean_subject(result["current_subject"])["clean"]
        prev_clean = clean_subject(result["previous_subject"])["clean"]
        
        if current_clean.lower() != prev_clean.lower():
            result["subject_changed"] = True
            result["thread_break"] = True
    
    return result


def extract_sender_from_html(html: str) -> dict:
    """
    Extract sender information from HTML headers.
    Returns: {name: str, email: str, raw: str}
    """
    result = {"name": "", "email": "", "raw": ""}
    
    patterns = [
        r'<b[^>]*>Van:|From:</b>\s*([^<]+(?:<[^>]+>[^<]+)*)<',
        r'<b[^>]*>Van:|From:</b>\s*([^<]+)',
        r'[\w\s]+<([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            raw = match.group(1).strip()
            result["raw"] = re.sub(r'<[^>]+>', '', raw).strip()
            
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', raw, re.IGNORECASE)
            if email_match:
                result["email"] = email_match.group(1).lower()
            
            name_match = re.search(r'^([^<]+?)(?:\s*<|$)', raw)
            if name_match:
                result["name"] = name_match.group(1).strip()
            
            if result["email"] or result["name"]:
                break
    
    return result


def parse_received_date(html: str) -> dict:
    """
    Parse received/sent date from HTML headers.
    Returns: {raw: str, parsed: str, timestamp: int or None}
    """
    result = {"raw": "", "parsed": "", "timestamp": None}
    
    import datetime
    
    patterns = [
        r'<b[^>]*>Verzonden:|Sent:</b>\s*([^<]+)',
        r'<b[^>]*>Date:</b>\s*([^<]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match and match.group(1):
            raw_date = match.group(1).strip()
            result["raw"] = raw_date
            
            try:
                from email.utils import parsedate_to_datetime
                parsed_dt = parsedate_to_datetime(raw_date)
                result["parsed"] = parsed_dt.isoformat()
                result["timestamp"] = int(parsed_dt.timestamp())
            except Exception:
                result["parsed"] = raw_date
            
            break
    
    return result


def calculate_confidence(html: str, extracted: str, original_length: int) -> dict:
    """
    Calculate confidence score for extraction quality.
    Returns: {score: float, factors: dict}
    """
    factors = {}
    score = 0.5
    
    if original_length == 0:
        return {"score": 0.0, "factors": {"empty_input": True}}
    
    extracted_length = len(extracted.strip())
    ratio = extracted_length / original_length if original_length > 0 else 1.0
    
    factors["ratio"] = ratio
    factors["extracted_length"] = extracted_length
    factors["original_length"] = original_length
    
    if ratio < 0.1:
        score = 0.95
        factors["ratio_factor"] = "excellent"
    elif ratio < 0.3:
        score = 0.85
        factors["ratio_factor"] = "good"
    elif ratio < 0.5:
        score = 0.7
        factors["ratio_factor"] = "moderate"
    elif ratio < 0.8:
        score = 0.5
        factors["ratio_factor"] = "low"
    else:
        score = 0.3
        factors["ratio_factor"] = "minimal_extraction"
    
    has_quoted_header = bool(re.search(
        r'<div[^>]*style="[^"]*border-top:solid|'
        r'<div[^>]*id="divRplyFwdMsg"|'
        r'<blockquote',
        html, re.IGNORECASE
    ))
    factors["has_quote_marker"] = has_quoted_header
    
    if has_quoted_header:
        score += 0.1
        if score > 1.0:
            score = 1.0
    
    extracted_text = re.sub(r'<[^>]+>', '', extracted).strip()
    if len(extracted_text) < 10 and extracted_length > 0:
        score -= 0.2
        factors["very_short"] = True
    
    return {
        "score": round(score, 2),
        "factors": factors
    }


def detect_thread_structure(html: str) -> dict:
    """
    Detect if email contains multiple messages (thread).
    Returns: {is_thread: bool, message_count: int, message_positions: list}
    """
    result = {
        "is_thread": False,
        "message_count": 1,
        "message_positions": [],
    }
    
    quote_markers = []
    
    o365_pattern = r'<div[^>]*id="divRplyFwdMsg"'
    for match in re.finditer(o365_pattern, html, re.IGNORECASE):
        quote_markers.append({"type": "o365", "position": match.start()})
    
    outlook_pattern = r'<div[^>]*style="[^"]*border-top:solid'
    for match in re.finditer(outlook_pattern, html, re.IGNORECASE):
        quote_markers.append({"type": "outlook_desktop", "position": match.start()})
    
    blockquote_pattern = r'<blockquote'
    for match in re.finditer(blockquote_pattern, html, re.IGNORECASE):
        quote_markers.append({"type": "blockquote", "position": match.start()})
    
    header_patterns = [
        r'<b[^>]*>Van:|From:</b>',
        r'<b[^>]*>Verzonden:|Sent:</b>',
        r'<b[^>]*>Onderwerp:|Subject:</b>',
    ]
    for pattern in header_patterns:
        for match in re.finditer(pattern, html, re.IGNORECASE):
            if match.start() > 500:
                quote_markers.append({"type": "header", "position": match.start()})
    
    quote_markers.sort(key=lambda x: x["position"])
    
    if len(quote_markers) > 1:
        result["is_thread"] = True
        result["message_count"] = len(quote_markers) + 1
        result["message_positions"] = [m["position"] for m in quote_markers]
    
    return result


def split_thread_messages(html: str) -> list:
    """
    Split thread into individual messages.
    Returns: list of message dicts with html and metadata
    """
    messages = []
    structure = detect_thread_structure(html)
    
    if not structure["is_thread"]:
        return [{"html": html, "is_newest": True, "index": 0}]
    
    positions = [0] + structure["message_positions"]
    
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(html)
        msg_html = html[start:end]
        
        msg_html = fix_html_structure(msg_html)
        
        messages.append({
            "html": msg_html,
            "is_newest": i == 0,
            "index": i,
        })
    
    return messages


def detect_forward(html: str) -> dict:
    """
    Enhanced forward detection from HTML content.
    Returns: {is_forward: bool, forward_count: int, has_original_attachment: bool}
    """
    result = {
        "is_forward": False,
        "forward_count": 0,
        "has_original_attachment": False,
    }
    
    forward_patterns = [
        r'<b[^>]*>Onderwerp:|Subject:</b>\s*FW[:\s]',
        r'<b[^>]*>Onderwerp:|Subject:</b>\s*Fwd[:\s]',
        r'---------- Forwarded message ----------',
        r'Begin forwarded message:',
    ]
    
    for pattern in forward_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        result["forward_count"] += len(matches)
    
    if result["forward_count"] > 0:
        result["is_forward"] = True
    
    attachment_patterns = [
        r'<a[^>]*href="cid:',
        r'<img[^>]*src="cid:',
    ]
    
    for pattern in attachment_patterns:
        if re.search(pattern, html, re.IGNORECASE):
            result["has_original_attachment"] = True
            break
    
    return result


PRE_PROCESSORS = [
    normalize_blockquotes,
    remove_outlook_web_reply_marker,
    remove_o365_reply_div,
    remove_o365_forward_div,
    remove_outlook_desktop_quoted_content,
    remove_gmail_quote_marker,
]


def apply_preprocessors(html: str) -> str:
    """Apply all pre-processors in order."""
    for processor in PRE_PROCESSORS:
        html = processor(html)
    return html
