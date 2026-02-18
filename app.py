import re
from talon import quotations

from flask import Flask, Response, request, jsonify

from preprocessing import (
    apply_preprocessors,
    detect_email_client,
    detect_reply_forward,
    extract_quoted_content,
    calculate_confidence,
    extract_sender_from_html,
    parse_received_date,
    detect_thread_structure,
    detect_forward,
    clean_subject,
    detect_subject_change,
)
from postprocessing import (
    apply_postprocessors,
    strip_html_to_text,
    extract_signature,
    sanitize_html,
    has_reply_content,
)

quotations.register_xpath_extensions()

app = Flask(__name__)


@app.route("/reply/extract_from_html", methods=["POST"])
def extract_from_html():
    """Extract quotations and return full response with HTML output."""
    original_html = request.get_data(as_text=True)
    original_length = len(original_html)
    include_signature = request.args.get("include_signature", "true").lower() == "true"
    include_full_thread = request.args.get("full_thread", "false").lower() == "true"
    
    if not original_html or original_length == 0:
        return jsonify({
            "success": False,
            "error": "Empty HTML input",
            "html": "",
            "text": "",
        }), 400
    
    try:
        format_detected = detect_email_client(original_html)
        reply_forward = detect_reply_forward(original_html)
        sender_info = extract_sender_from_html(original_html)
        date_info = parse_received_date(original_html)
        thread_structure = detect_thread_structure(original_html)
        forward_info = detect_forward(original_html)
        
        subject_match = re.search(r'<b[^>]*>Onderwerp:</b>\s*([^<]+)', original_html, re.IGNORECASE)
        if not subject_match:
            subject_match = re.search(r'<b[^>]*>Subject:</b>\s*([^<]+)', original_html, re.IGNORECASE)
        current_subject = subject_match.group(1).strip() if subject_match and subject_match.group(1) else ""
        
        subject_info = clean_subject(current_subject)
        subject_change = detect_subject_change(original_html)
        
        cleaned_html, quoted_html = extract_quoted_content(original_html, format_detected)
        
        html = apply_preprocessors(cleaned_html)
        extracted = quotations.extract_from_html(html)
        extracted = apply_postprocessors(extracted)
        
        extracted, signature = extract_signature(extracted, include_signature)
        
        plain_text = strip_html_to_text(extracted)
        
        confidence = calculate_confidence(html, extracted, original_length)
        ratio = len(extracted) / original_length if original_length > 0 else 1.0
        
        response_data = {
            "success": True,
            "html": extracted,
            "text": plain_text,
            "original_html": original_html,
            "quoted_html": quoted_html,
            "signature": signature,
            "attachments": [],
            "original_length": original_length,
            "extracted_length": len(extracted),
            "ratio": ratio,
            "format_detected": format_detected,
            "confidence": confidence,
            "metadata": {
                "has_reply": has_reply_content(extracted, original_length),
                "is_forward": reply_forward.get("is_forward", False) or forward_info.get("is_forward", False),
                "is_reply": reply_forward.get("is_reply", False),
                "sender": sender_info,
                "date": date_info,
                "thread": thread_structure,
                "forward": forward_info,
                "subject": subject_info,
                "subject_change": subject_change,
            },
        }
        
        if include_full_thread:
            from preprocessing import split_thread_messages
            from postprocessing import sanitize_html
            messages = split_thread_messages(original_html)
            processed_messages = []
            for msg in messages:
                msg_html = apply_preprocessors(msg["html"])
                msg_extracted = quotations.extract_from_html(msg_html)
                msg_extracted = apply_postprocessors(msg_extracted)
                msg_extracted, msg_sig = extract_signature(msg_extracted, include_signature)
                processed_messages.append({
                    "html": msg_extracted,
                    "text": strip_html_to_text(msg_extracted),
                    "is_newest": msg["is_newest"],
                    "index": msg["index"],
                })
            response_data["thread_messages"] = processed_messages
        
        return jsonify(response_data)
    except Exception as e:
        import traceback
        app.logger.error(f"Extraction error: {e}\n{traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e),
            "html": original_html,
            "text": strip_html_to_text(original_html),
        }), 500


@app.route("/reply/extract_from_html/plain", methods=["POST"])
def extract_from_html_plain():
    """Same as above but returns plain text as primary output."""
    original_html = request.get_data(as_text=True)
    original_length = len(original_html)
    include_signature = request.args.get("include_signature", "true").lower() == "true"
    include_full_thread = request.args.get("full_thread", "false").lower() == "true"
    
    if not original_html or original_length == 0:
        return jsonify({
            "success": False,
            "error": "Empty HTML input",
            "html": "",
            "text": "",
        }), 400
    
    try:
        format_detected = detect_email_client(original_html)
        reply_forward = detect_reply_forward(original_html)
        sender_info = extract_sender_from_html(original_html)
        date_info = parse_received_date(original_html)
        thread_structure = detect_thread_structure(original_html)
        forward_info = detect_forward(original_html)
        
        subject_match = re.search(r'<b[^>]*>Onderwerp:</b>\s*([^<]+)', original_html, re.IGNORECASE)
        if not subject_match:
            subject_match = re.search(r'<b[^>]*>Subject:</b>\s*([^<]+)', original_html, re.IGNORECASE)
        current_subject = subject_match.group(1).strip() if subject_match and subject_match.group(1) else ""
        
        subject_info = clean_subject(current_subject)
        subject_change = detect_subject_change(original_html)
        
        cleaned_html, quoted_html = extract_quoted_content(original_html, format_detected)
        
        html = apply_preprocessors(cleaned_html)
        extracted = quotations.extract_from_html(html)
        extracted = apply_postprocessors(extracted)
        
        extracted, signature = extract_signature(extracted, include_signature)
        plain_text = strip_html_to_text(extracted)
        
        confidence = calculate_confidence(html, extracted, original_length)
        ratio = len(plain_text) / original_length if original_length > 0 else 1.0
        
        response_data = {
            "success": True,
            "text": plain_text,
            "html": extracted,
            "original_html": original_html,
            "quoted_html": quoted_html,
            "signature": signature,
            "attachments": [],
            "original_length": original_length,
            "extracted_length": len(plain_text),
            "ratio": ratio,
            "format_detected": format_detected,
            "confidence": confidence,
            "metadata": {
                "has_reply": has_reply_content(extracted, original_length),
                "is_forward": reply_forward.get("is_forward", False) or forward_info.get("is_forward", False),
                "is_reply": reply_forward.get("is_reply", False),
                "sender": sender_info,
                "date": date_info,
                "thread": thread_structure,
                "forward": forward_info,
                "subject": subject_info,
                "subject_change": subject_change,
            },
        }
        
        if include_full_thread:
            from preprocessing import split_thread_messages
            messages = split_thread_messages(original_html)
            processed_messages = []
            for msg in messages:
                msg_html = apply_preprocessors(msg["html"])
                msg_extracted = quotations.extract_from_html(msg_html)
                msg_extracted = apply_postprocessors(msg_extracted)
                msg_extracted, msg_sig = extract_signature(msg_extracted, include_signature)
                processed_messages.append({
                    "html": msg_extracted,
                    "text": strip_html_to_text(msg_extracted),
                    "is_newest": msg["is_newest"],
                    "index": msg["index"],
                })
            response_data["thread_messages"] = processed_messages
        
        return jsonify(response_data)
    except Exception as e:
        app.logger.error(f"Extraction error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "html": original_html,
            "text": strip_html_to_text(original_html),
        }), 500


@app.route("/health")
def health():
    return Response("OK", status=200)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
