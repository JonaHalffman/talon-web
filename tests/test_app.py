import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client():
    """Create test client for the Flask app."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_gmail_html():
    """Sample Gmail HTML with blockquote."""
    return """<html><body>
<p>This is my reply</p>
<blockquote class="gmail_quote">
<p>This is the quoted content from the original email.</p>
</blockquote>
</body></html>"""


@pytest.fixture
def sample_outlook_desktop_html():
    """Sample Outlook Desktop HTML with border-top."""
    return """<html><body>
<p>This is my reply</p>
<div><div style="border:none; border-top:solid #E1E1E1 1.0pt; padding:3.0pt 0cm 0cm 0cm">
<p class="MsoNormal"><b>Van:</b> sender@example.com<br>
<b>Verzonden:</b> maandag 9 febrero 2026 7:48<br>
<b>Onderwerp:</b> Original Subject</p>
</div></div>
<p>Original message content here...</p>
</body></html>"""


@pytest.fixture
def sample_plain_email_html():
    """Sample email without quoted content."""
    return """<html><body>
<p>This is a standalone email without replies.</p>
<p>Just some content.</p>
</body></html>"""


class TestExtractEndpoint:
    """Tests for /reply/extract_from_html endpoint."""

    def test_extract_gmail_quote(self, client, sample_gmail_html):
        """Test extraction of Gmail-style quotes."""
        response = client.post(
            '/reply/extract_from_html',
            data=sample_gmail_html,
            content_type='text/html'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'extracted' in data
        assert 'ratio' in data
        assert 'original_length' in data
        assert 'extracted_length' in data
        
        # Gmail quote should be extracted (ratio < 1.0)
        assert data['ratio'] < 1.0

    def test_extract_outlook_desktop(self, client, sample_outlook_desktop_html):
        """Test extraction of Outlook Desktop quotes."""
        response = client.post(
            '/reply/extract_from_html',
            data=sample_outlook_desktop_html,
            content_type='text/html'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Outlook desktop quote should be extracted
        assert data['ratio'] < 1.0

    def test_plain_email_no_extraction(self, client, sample_plain_email_html):
        """Test that plain emails return ratio of 1.0."""
        response = client.post(
            '/reply/extract_from_html',
            data=sample_plain_email_html,
            content_type='text/html'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # No quote to extract, ratio should be 1.0
        assert data['ratio'] == 1.0

    def test_empty_body(self, client):
        """Test handling of empty request body."""
        response = client.post(
            '/reply/extract_from_html',
            data='',
            content_type='text/html'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['ratio'] == 1.0

    def test_returns_valid_json(self, client, sample_plain_email_html):
        """Test that response is valid JSON."""
        response = client.post(
            '/reply/extract_from_html',
            data=sample_plain_email_html,
            content_type='text/html'
        )
        
        assert response.status_code == 200
        
        # Should be parseable as JSON
        data = json.loads(response.data)
        assert isinstance(data, dict)


class TestExtractPlainEndpoint:
    """Tests for /reply/extract_from_html/plain endpoint."""

    def test_plain_text_output(self, client, sample_gmail_html):
        """Test plain text endpoint returns text field."""
        response = client.post(
            '/reply/extract_from_html/plain',
            data=sample_gmail_html,
            content_type='text/html'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'text' in data
        assert 'ratio' in data
        
        # Plain text should be shorter than original
        assert data['ratio'] < 1.0

    def test_html_stripped(self, client, sample_gmail_html):
        """Test that HTML tags are stripped in plain output."""
        response = client.post(
            '/reply/extract_from_html/plain',
            data=sample_gmail_html,
            content_type='text/html'
        )
        
        data = json.loads(response.data)
        
        # Plain text should not contain HTML tags
        assert '<' not in data['text'] or data['text'].count('<') < 2


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check(self, client):
        """Test health check returns OK."""
        response = client.get('/health')
        
        assert response.status_code == 200
        assert response.data == b'OK'

    def test_health_check_content_type(self, client):
        """Test health check returns correct content type."""
        response = client.get('/health')
        
        assert response.content_type == 'text/html; charset=utf-8'
