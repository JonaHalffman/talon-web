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
    """
    pattern = r'<div[^>]*style="[^"]*border-top:solid[^"]*"[^>]*>.*'
    
    return re.sub(pattern, '', html, flags=re.DOTALL | re.IGNORECASE)


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
    
    return html, quoted_html


def detect_reply_forward(html: str) -> dict:
    """
    Detect if email is a reply or forward from subject/headers.
    Returns: {is_reply: bool, is_forward: bool}
    """
    is_reply = False
    is_forward = False
    
    subject_match = re.search(r'<b[^>]*>Onderwerp:|Subject:</b>\s*([^<]+)', html, re.IGNORECASE)
    if subject_match:
        subject = subject_match.group(1).lower()
        if subject.startswith('re:'):
            is_reply = True
        elif subject.startswith('fw:') or subject.startswith('fw:'):
            is_forward = True
    
    return {"is_reply": is_reply, "is_forward": is_forward}


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
