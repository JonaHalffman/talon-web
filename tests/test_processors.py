import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preprocessing import (
    remove_o365_reply_div,
    remove_outlook_web_reply_marker,
    remove_outlook_desktop_quoted_content,
    apply_preprocessors,
)
from postprocessing import (
    strip_html_to_text,
    clean_empty_divs,
    detect_quoted_signature_lines,
    apply_postprocessors,
)


class TestPreprocessors:
    """Tests for pre-processing functions."""

    def test_remove_o365_reply_div(self):
        """Test O365 reply div removal."""
        html = """<html><body>
<div>New reply content</div>
<div id="divRplyFwdMsg">Reply marker</div>
<div><div style="border-top:solid #E1E1E1">
<p>Quoted content</p>
</div></div>
</body></html>"""
        
        result = remove_o365_reply_div(html)
        
        # The reply marker div should be removed
        assert 'divRplyFwdMsg' not in result

    def test_remove_outlook_web_reply_marker(self):
        """Test Outlook Web reply marker removal."""
        html = """<html><body>
<p>New content</p>
<div id="divRplyFwdMsg">Some reply marker</div>
<div class="RplyEdtPrsngMsg">Another marker</div>
</body></html>"""
        
        result = remove_outlook_web_reply_marker(html)
        
        # Reply markers should be removed
        assert 'divRplyFwdMsg' not in result
        assert 'RplyEdtPrsngMsg' not in result
        # But new content should remain
        assert 'New content' in result

    def test_remove_outlook_desktop_quoted_content(self):
        """Test Outlook Desktop border-top removal."""
        html = """<html><body>
<p>New reply content</p>
<div><div style="border:none; border-top:solid #E1E1E1 1.0pt">
<p class="MsoNormal"><b>Van:</b> sender@example.com</p>
<p>Original message content</p>
</div></div>
</body></html>"""
        
        result = remove_outlook_desktop_quoted_content(html)
        
        # Border-top and everything after should be removed
        assert 'New reply content' in result
        assert 'Original message' not in result

    def test_apply_preprocessors(self):
        """Test full pre-processing pipeline."""
        html = """<html><body>
<p>New reply</p>
<div id="divRplyFwdMsg">Marker</div>
<div style="border-top:solid #E1E1E1">
<p>Quoted</p>
</div>
</body></html>"""
        
        result = apply_preprocessors(html)
        
        # Both markers and quoted content should be removed
        assert 'New reply' in result
        assert 'Quoted' not in result

    def test_no_change_for_simple_email(self):
        """Test that simple emails aren't modified."""
        html = """<html><body>
<p>Simple email content without quotes.</p>
</body></html>"""
        
        result = apply_preprocessors(html)
        
        # Content should remain unchanged
        assert 'Simple email' in result


class TestPostprocessors:
    """Tests for post-processing functions."""

    def test_strip_html_to_text(self):
        """Test HTML to plain text conversion."""
        html = """<html><body>
<p>Line one</p>
<p>Line two</p>
<br>
<p>Line three</p>
</body></html>"""
        
        result = strip_html_to_text(html)
        
        # Should have newlines where paragraphs were
        assert 'Line one' in result
        assert 'Line two' in result
        # Should not have HTML tags
        assert '<p>' not in result

    def test_strip_html_entities(self):
        """Test HTML entity decoding."""
        html = """<html><body>
<p>Hello&nbsp;World</p>
<p>Less than: &lt;tag&gt;</p>
<p>Ampersand: &amp; Co</p>
</body></html>"""
        
        result = strip_html_to_text(html)
        
        # Entities should be decoded
        assert '&nbsp;' not in result
        assert 'Hello World' in result

    def test_clean_empty_divs(self):
        """Test empty div removal."""
        html = """<html><body>
<p>Content</p>
<div></div>
<div>&nbsp;</div>
<p>&nbsp;</p>
</body></html>"""
        
        result = clean_empty_divs(html)
        
        # Empty elements should be removed
        assert '<div></div>' not in result

    def test_detect_quoted_signature_lines_dutch(self):
        """Test detection of Dutch signature lines."""
        html = """<html><body>
<p>Some content</p>
<div><div style="border-top:solid">
<p><b>Van:</b> sender@example.com</p>
<p><b>Verzonden:</b> maandag 9 febrero 2026</p>
</div></div>
</body></html>"""
        
        result = detect_quoted_signature_lines(html)
        
        assert result is True

    def test_detect_quoted_signature_lines_english(self):
        """Test detection of English signature lines."""
        html = """<html><body>
<p>Some content</p>
<p><b>From:</b> sender@example.com</p>
<p><b>Sent:</b> Monday 9 February 2026</p>
</body></html>"""
        
        result = detect_quoted_signature_lines(html)
        
        assert result is True

    def test_detect_no_quotes(self):
        """Test that plain emails return False."""
        html = """<html><body>
<p>Just some content without quotes.</p>
</body></html>"""
        
        result = detect_quoted_signature_lines(html)
        
        assert result is False

    def test_apply_postprocessors(self):
        """Test full post-processing pipeline."""
        html = """<html><body>
<p>Content</p>
<div></div>
</body></html>"""
        
        result = apply_postprocessors(html)
        
        # Empty divs should be cleaned
        assert '<div></div>' not in result
