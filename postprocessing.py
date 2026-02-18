"""
Post-processing functions for extracted HTML after quotation extraction.
Each function should accept HTML string and return modified HTML string.
"""

import re
from typing import Optional, Tuple, List


def strip_html_to_text(html: str) -> str:
    """Convert HTML to plain text."""
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&amp;', '&')
    text = text.replace('&#160;', ' ')
    text = text.replace('&#xA0;', ' ')
    
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()
    
    return text


def extract_signature(html: str) -> Tuple[str, str]:
    """
    Extract signature from HTML.
    Returns: (html_without_signature, signature_text)
    """
    signature = ""
    
    patterns = [
        r'(<div[^>]*class="[^"]*signature[^"]*"[^>]*>.*?)',
        r'(<p[^>]*>--\s*</p>.*?)',
        r'(<div[^>]*>\s*--\s*<br\s*/?>.*?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            signature = match.group(1)
            html = html[:match.start()] + html[match.end():]
            break
    
    if not signature:
        text = strip_html_to_text(html)
        lines = text.split('\n')
        if len(lines) > 2:
            last_lines = lines[-5:]
            for i, line in enumerate(last_lines):
                if re.match(r'^[\s-]*$', line):
                    continue
                if re.match(r'^[\s]*[\w\s]+[\s]*$', line):
                    if i > 0:
                        signature = '\n'.join(last_lines[i:])
                        html_lines = lines[:-5 + i] if i < 5 else lines[:-5]
                        html = '\n'.join(html_lines)
                        break
    
    return html, signature


def extract_first_message_only(html: str) -> str:
    """Extract only the first (newest) message from extracted HTML."""
    patterns = [
        r'<div[^>]*style="border-top:solid',
        r'<blockquote',
        r'--\s*$',
    ]
    
    for pattern in patterns:
        parts = re.split(pattern, html, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) > 1:
            html = parts[0]
    
    return html


def clean_empty_divs(html: str) -> str:
    """Remove empty divs and common placeholder content."""
    html = re.sub(r'<div[^>]*>\s*(&nbsp;|\s)*\s*</div>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<p[^>]*>\s*(&nbsp;|\s)*\s*</p>', '', html, flags=re.IGNORECASE)
    
    return html


def sanitize_html(html: str) -> str:
    """
    Sanitize HTML by removing potentially dangerous elements.
    - Removes <script> tags and inline JavaScript
    - Removes 1x1 tracking pixels
    - Removes dangerous elements (iframes, objects, etc.)
    """
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r'<script[^>]*/>', '', html, flags=re.IGNORECASE)
    
    html = re.sub(
        r'<img[^>]*width="1"[^>]*height="1"[^>]*>',
        '',
        html,
        flags=re.IGNORECASE
    )
    html = re.sub(
        r'<img[^>]*height="1"[^>]*width="1"[^>]*>',
        '',
        html,
        flags=re.IGNORECASE
    )
    
    dangerous_tags = ['iframe', 'object', 'embed', 'applet', 'link']
    for tag in dangerous_tags:
        html = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(rf'<{tag}[^>]*/?>', '', html, flags=re.IGNORECASE)
    
    html = re.sub(r'on\w+\s*=\s*["\'].*?["\']', '', html, flags=re.IGNORECASE)
    html = re.sub(r'on\w+\s*=\s*[^\s>]+', '', html, flags=re.IGNORECASE)
    
    return html


def detect_quoted_signature_lines(html: str) -> bool:
    """Detect if HTML contains quoted signature lines."""
    patterns = [
        r'<b>Van:</b>',
        r'<b>Verzonden:</b>',
        r'<b>Onderwerp:</b>',
        r'<b>From:</b>',
        r'<b>Sent:</b>',
    ]
    
    for pattern in patterns:
        if re.search(pattern, html, re.IGNORECASE):
            return True
    
    return False


def has_reply_content(html: str, original_length: int) -> bool:
    """Determine if extracted content is a reply vs original message."""
    if original_length == 0:
        return False
    
    extracted_length = len(html.strip())
    if extracted_length == 0:
        return False
    
    ratio = extracted_length / original_length
    return ratio < 0.95


POST_PROCESSORS = [
    clean_empty_divs,
    sanitize_html,
]


def apply_postprocessors(html: str) -> str:
    """Apply all post-processors in order."""
    for processor in POST_PROCESSORS:
        html = processor(html)
    return html
