import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preprocessing import (
    remove_o365_reply_div,
    remove_outlook_web_reply_marker,
    remove_outlook_desktop_quoted_content,
    apply_preprocessors,
    detect_thread_structure,
    detect_forward,
)
from postprocessing import (
    strip_html_to_text,
    clean_empty_divs,
    detect_quoted_signature_lines,
    apply_postprocessors,
    extract_signature,
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


class TestSignatureExtraction:
    """Tests for signature extraction."""

    def test_extract_signature_dash_dash(self):
        """Test extraction of -- signature separator."""
        html = """<html><body>
        <p>Hello, this is my reply.</p>
        <p>--</p>
        <p>John Doe</p>
        <p>john@example.com</p>
        </body></html>"""
        
        result, signature = extract_signature(html)
        
        assert 'John Doe' in signature
        assert 'john@example.com' in signature

    def test_extract_signature_with_include_false(self):
        """Test signature exclusion when include_signature=False."""
        html = """<html><body>
        <p>Hello, this is my reply.</p>
        <p>--</p>
        <p>John Doe</p>
        </body></html>"""
        
        result, signature = extract_signature(html, include_signature=False)
        
        assert signature == ""
        assert 'John Doe' in result

    def test_extract_signature_div_class(self):
        """Test extraction of signature div."""
        html = """<html><body>
        <p>Reply content</p>
        <div class="signature">
        <p>Jane Smith</p>
        <p>jane@company.com</p>
        </div>
        </body></html>"""
        
        result, signature = extract_signature(html)
        
        assert 'Jane Smith' in signature
        assert 'jane@company.com' in signature

    def test_extract_no_signature(self):
        """Test that emails without signatures return empty string."""
        html = """<html><body>
        <p>Just a simple reply without any signature.</p>
        </body></html>"""
        
        result, signature = extract_signature(html)
        
        assert signature == ""


class TestThreadDetection:
    """Tests for thread detection and splitting."""

    def test_detect_simple_email_no_thread(self):
        """Test that simple emails are not detected as threads."""
        html = """<html><body>
        <p>Just a simple reply without any quoted content.</p>
        </body></html>"""
        
        result = detect_thread_structure(html)
        
        assert result["is_thread"] is False
        assert result["message_count"] == 1

    def test_detect_thread_with_border_top(self):
        """Test thread detection with border-top marker and header."""
        html = """<html><body>
        <p>Newest reply that is quite long and has lots of content to push the position past 500 characters to trigger the header detection logic in the function</p>
        <p>Additional content to make it even longer so the header will be detected as a second marker in the thread structure detection</p>
        <p>More content to ensure we pass the 500 character threshold that is hardcoded in the detect_thread_structure function</p>
        <div style="border:none; border-top:solid #E1E1E1 1.0pt">
        <p><b>Van:</b> sender@example.com</p>
        <p><b>Verzonden:</b> maandag 17 feb 2026</p>
        <p>Older message content</p>
        </div>
        </body></html>"""
        
        result = detect_thread_structure(html)
        
        assert result["message_count"] >= 2

    def test_detect_thread_with_blockquote_and_header(self):
        """Test thread detection with blockquote and header markers."""
        html = """<html><body>
        <p>Reply content here with enough text to push past position 500 to trigger header detection in the function</p>
        <p>Additional paragraph to ensure we have enough content before the quoted section to trigger proper thread detection</p>
        <p>Even more content to make sure the 500 character threshold is definitely met for the header detection logic in the code</p>
        <p>Adding even more text here to ensure we pass the threshold and can test the thread detection properly</p>
        <blockquote type="cite">
        <b>From:</b> sender@example.com
        <p>Quoted content</p>
        </blockquote>
        </body></html>"""
        
        result = detect_thread_structure(html)
        
        assert result["message_count"] >= 2

    def test_detect_forward(self):
        """Test forward detection."""
        html = """<html><body>
        <p>Forwarded message</p>
        <b>Onderwerp:</b> FW: Original Subject
        </body></html>"""
        
        result = detect_forward(html)
        
        assert result["is_forward"] is True
        assert result["forward_count"] >= 1

    def test_detect_no_forward(self):
        """Test that normal replies are not marked as forwards."""
        html = """<html><body>
        <p>Just a regular reply</p>
        </body></html>"""
        
        result = detect_forward(html)
        
        assert result["is_forward"] is False
        assert result["forward_count"] == 0


class TestSubjectProcessing:
    """Tests for subject line processing."""

    def test_clean_subject_re_prefix(self):
        """Test RE: prefix removal."""
        from preprocessing import clean_subject
        
        result = clean_subject("RE: Original Subject")
        
        assert result["is_reply"] is True
        assert result["clean"] == "Original Subject"
        assert "RE" in result["prefix"]

    def test_clean_subject_fw_prefix(self):
        """Test FW: prefix removal."""
        from preprocessing import clean_subject
        
        result = clean_subject("FW: Forwarded Subject")
        
        assert result["is_forward"] is True
        assert result["clean"] == "Forwarded Subject"
        assert "FW" in result["prefix"]

    def test_clean_subject_re_bracket(self):
        """Test RE[n]: bracket prefix removal."""
        from preprocessing import clean_subject
        
        result = clean_subject("RE[3]: Original Subject")
        
        assert result["is_reply"] is True
        assert result["clean"] == "Original Subject"

    def test_clean_subject_dutch_aw(self):
        """Test Dutch AW (Antwoord) prefix removal."""
        from preprocessing import clean_subject
        
        result = clean_subject("AW: Reactie op bericht")
        
        assert result["is_reply"] is True
        assert result["clean"] == "Reactie op bericht"

    def test_clean_subject_no_prefix(self):
        """Test subject without prefix."""
        from preprocessing import clean_subject
        
        result = clean_subject("Just a regular subject")
        
        assert result["is_reply"] is False
        assert result["is_forward"] is False
        assert result["clean"] == "Just a regular subject"

    def test_detect_subject_change(self):
        """Test subject change detection in threads."""
        from preprocessing import detect_subject_change
        
        html = """<html><body>
        <p>New reply with enough content to push past 500 characters so that header detection works properly in the thread structure</p>
        <p>Additional content to ensure we pass the threshold for proper header detection</p>
        <b>Onderwerp:</b> Completely Different Subject
        <b>Van:</b> sender@example.com
        <p>More content...</p>
        <b>Onderwerp:</b> Original Subject
        <p>Old content</p>
        </body></html>"""
        
        result = detect_subject_change(html)
        
        assert result["subject_changed"] is True
        assert result["thread_break"] is True
        assert result["current_subject"] == "Completely Different Subject"
        assert result["previous_subject"] == "Original Subject"

    def test_detect_no_subject_change(self):
        """Test that same subjects don't trigger change detection."""
        from preprocessing import detect_subject_change
        
        html = """<html><body>
        <p>Reply</p>
        <b>Onderwerp:</b> RE: Same Subject
        <b>Van:</b> sender@example.com
        </body></html>"""
        
        result = detect_subject_change(html)
        
        assert result["subject_changed"] is False
        assert result["thread_break"] is False
