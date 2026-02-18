"""
Pre-processing functions for email HTML before quotation extraction.
Each function should accept HTML string and return modified HTML string.
"""

import re
from typing import Optional, Tuple


def detect_email_client(html: str) -> str:
    """
    Detect the email client format from HTML.
    Returns: o365, outlook_desktop, gmail, apple_mail, yahoo, unknown
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
    
    return "unknown"


def remove_o365_reply_div(html: str) -> str:
    """
    Remove O365 reply marker div and following quoted content div.
    Talon's cut_microsoft_quote() finds the marker but misses sibling divs.
    """
    patterns = [
        r'<div[^>]*id="divRplyFwdMsg"[^>]*>.*?</div>\s*<div[^>]*>',
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
    """Remove Gmail quoted content markers."""
    return html


def normalize_blockquotes(html: str) -> str:
    """Normalize various blockquote formats for better talon detection."""
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


PRE_PROCESSORS = [
    remove_outlook_web_reply_marker,
    remove_o365_reply_div,
    remove_outlook_desktop_quoted_content,
]


def apply_preprocessors(html: str) -> str:
    """Apply all pre-processors in order."""
    for processor in PRE_PROCESSORS:
        html = processor(html)
    return html
