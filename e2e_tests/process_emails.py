"""
Process emails through talon-web API and save results.
Orchestrates Docker startup, email processing, and report generation.
"""

import os
import sys
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from email import policy
from email.parser import BytesParser

import requests
import yaml
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class TalonProcessor:
    """Processes emails through talon-web API."""

    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.base_output_dir = Path(self.config.get("output", {}).get("base_dir", "outputs"))
        self.originals_dir = self.base_output_dir / self.config.get("output", {}).get("originals_subdir", "originals")
        self.html_dir = self.base_output_dir / self.config.get("output", {}).get("html_subdir", "html_bodies")
        self.processed_dir = self.base_output_dir / self.config.get("output", {}).get("processed_subdir", "processed")
        self.reports_dir = self.base_output_dir / self.config.get("output", {}).get("reports_subdir", "reports")

        self.html_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.talon_config = self.config.get("talon_web", {})
        self.talon_host = self.talon_config.get("host", "localhost")
        self.talon_port = self.talon_config.get("port", 5000)
        self.base_url = f"http://{self.talon_host}:{self.talon_port}"

    def _load_config(self, config_path: Optional[str]) -> dict:
        """Load configuration from YAML file."""
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        if Path(config_path).exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}

    def check_talon_health(self) -> bool:
        """Check if talon-web is running and healthy."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200 and response.text == "OK":
                logger.info("talon-web is healthy")
                return True
        except requests.exceptions.RequestException:
            pass
        return False

    def wait_for_talon(self, timeout: int = 60) -> bool:
        """Wait for talon-web to become available."""
        logger.info(f"Waiting for talon-web at {self.base_url}...")
        start = time.time()
        while time.time() - start < timeout:
            if self.check_talon_health():
                return True
            time.sleep(2)
        logger.error("talon-web did not become available in time")
        return False

    def start_docker(self) -> bool:
        """Start talon-web Docker container."""
        import docker

        try:
            client = docker.from_env()
            container_name = self.talon_config.get("docker_container", "talon-web-e2e")
            image_name = self.talon_config.get("docker_image", "talon-web")

            existing = client.containers.get(container_name)
            if existing.status == "running":
                logger.info(f"Container {container_name} already running")
                return True
            else:
                logger.info(f"Starting existing container {container_name}")
                existing.start()
                return self.wait_for_talon()

        except docker.errors.NotFound:
            logger.info(f"Container {container_name} not found, building image...")
            return self.build_and_run_docker()
        except Exception as e:
            logger.error(f"Docker error: {e}")
            return False

    def build_and_run_docker(self) -> bool:
        """Build and run Docker container."""
        import docker

        try:
            client = docker.from_env()
            image_name = self.talon_config.get("docker_image", "talon-web")
            project_dir = Path(__file__).parent.parent

            logger.info("Building Docker image...")
            image, build_logs = client.images.build(
                path=str(project_dir),
                tag=image_name,
                rm=True
            )
            for log in build_logs:
                if "stream" in log:
                    logger.info(log["stream"].strip())

            container_name = self.talon_config.get("docker_container", "talon-web-e2e")
            port = self.talon_config.get("port", 5000)

            logger.info("Starting container...")
            container = client.containers.run(
                image_name,
                name=container_name,
                ports={"5000/tcp": port},
                detach=True,
                remove=False
            )

            logger.info(f"Container started: {container.short_id}")
            return self.wait_for_talon()

        except docker.errors.BuildError as e:
            logger.error(f"Build error: {e}")
            return False
        except Exception as e:
            logger.error(f"Docker error: {e}")
            return False

    def stop_docker(self) -> bool:
        """Stop talon-web Docker container."""
        import docker

        try:
            client = docker.from_env()
            container_name = self.talon_config.get("docker_container", "talon-web-e2e")
            container = client.containers.get(container_name)
            container.stop(timeout=10)
            logger.info(f"Stopped container {container_name}")
            return True
        except docker.errors.NotFound:
            logger.info(f"Container {container_name} not found")
            return True
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
            return False

    def extract_html_from_eml(self, eml_path: Path) -> Optional[str]:
        """Extract HTML body from .eml file."""
        try:
            with open(eml_path, "rb") as f:
                msg = BytesParser(policy=policy.default).parse(f)

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/html":
                        return part.get_content()
            else:
                content_type = msg.get_content_type()
                if content_type == "text/html":
                    return msg.get_content()

            return None
        except Exception as e:
            logger.error(f"Error parsing EML: {e}")
            return None

    def process_email(self, html_content: str, email_meta: dict) -> dict:
        """Send HTML to talon-web and get extraction result."""
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.base_url}/reply/extract_from_html",
                data=html_content.encode("utf-8"),
                headers={"Content-Type": "text/html; charset=utf-8"},
                timeout=30
            )

            processing_time = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": data.get("success", True),
                    "status_code": response.status_code,
                    "original_length": data.get("original_length", len(html_content)),
                    "extracted_length": data.get("extracted_length", 0),
                    "ratio": data.get("ratio", 1.0),
                    "processing_time_ms": processing_time,
                    "extracted_html": data.get("html", ""),
                    "extracted_text": data.get("text", ""),
                    "quoted_html": data.get("quoted_html", ""),
                    "signature": data.get("signature", ""),
                    "format_detected": data.get("format_detected", "unknown"),
                    "metadata": data.get("metadata", {}),
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text[:500],
                    "processing_time_ms": processing_time
                }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timeout",
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }

    def process_all_emails(self, start_docker: bool = True, stop_docker: bool = True) -> list:
        """Process all emails in the originals directory."""
        metadata_path = self.originals_dir / "metadata.json"
        if not metadata_path.exists():
            logger.error(f"Metadata file not found: {metadata_path}")
            logger.error("Run fetch_emails.py first to download emails")
            return []

        with open(metadata_path) as f:
            emails = json.load(f)

        if not emails:
            logger.warning("No emails found to process")
            return []

        if start_docker:
            if not self.start_docker():
                logger.error("Failed to start talon-web")
                return []
            logger.info("Docker started, ready to process")

        results = []
        for email_meta in emails:
            html_content = None
            html_path = None
            
            # First check if we have HTML file path (from --html-only mode)
            html_file = email_meta.get("html_file")
            if html_file:
                html_path = Path(html_file)
                if html_path.exists():
                    with open(html_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
            
            # Fall back to extracting from EML if no HTML file
            if not html_content:
                eml_file = email_meta.get("eml_file")
                if not eml_file:
                    logger.warning(f"No html_file or eml_file for email {email_meta.get('index')}")
                    continue

                eml_path = Path(eml_file)
                if not eml_path.exists():
                    logger.warning(f"EML file not found: {eml_path}")
                    continue

                html_content = self.extract_html_from_eml(eml_path)
                if html_content:
                    # Save extracted HTML
                    html_filename = eml_path.stem + ".html"
                    html_path = self.html_dir / html_filename
                    with open(html_path, "w", encoding="utf-8") as f:
                        f.write(html_content)

            if not html_content:
                logger.warning(f"  No HTML body found for: {email_meta.get('subject', 'No Subject')[:50]}...")
                continue

            logger.info(f"\nProcessing: {email_meta.get('subject', 'No Subject')[:50]}...")

            result = self.process_email(html_content, email_meta)

            result.update({
                "index": email_meta.get("index"),
                "message_id": email_meta.get("message_id"),
                "subject": email_meta.get("subject"),
                "from": email_meta.get("from"),
                "received": email_meta.get("received"),
                "has_attachments": email_meta.get("has_attachments"),
                "original_file": str(eml_path) if email_meta.get("eml_file") else None,
                "html_file": str(html_path)
            })

            output_filename = f"result_{email_meta.get('index'):03d}.json"
            output_path = self.processed_dir / output_filename

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            logger.info(f"  Success: {result.get('success')}")
            if result.get("success"):
                logger.info(f"  Original: {result.get('original_length')} chars")
                logger.info(f"  Extracted: {result.get('extracted_length')} chars")
                logger.info(f"  Ratio: {result.get('ratio', 0):.2%}")
            else:
                logger.error(f"  Error: {result.get('error', 'Unknown')[:100]}")

            results.append(result)

        if stop_docker:
            logger.info("\nStopping Docker...")
            self.stop_docker()

        return results

    def generate_report(self, results: list) -> dict:
        """Generate summary report."""
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_processed": len(results),
            "successful": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
            "total_original_chars": sum(r.get("original_length", 0) for r in results if r.get("success")),
            "total_extracted_chars": sum(r.get("extracted_length", 0) for r in results if r.get("success")),
            "avg_processing_time_ms": sum(r.get("processing_time_ms", 0) for r in results) / len(results) if results else 0,
            "results": results
        }

        summary_path = self.reports_dir / "summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        logger.info(f"\n{'='*50}")
        logger.info("PROCESSING SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Total processed: {summary['total_processed']}")
        logger.info(f"Successful: {summary['successful']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info(f"Avg processing time: {summary['avg_processing_time_ms']:.0f}ms")
        logger.info(f"\nDetailed report: {summary_path}")

        return summary


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Process emails through talon-web")
    parser.add_argument("--input-dir", help="Directory with original .eml files")
    parser.add_argument("--output-dir", help="Directory for processed results")
    parser.add_argument("--no-start-docker", action="store_true",
                       help="Don't start Docker (assume already running)")
    parser.add_argument("--no-stop-docker", action="store_true",
                       help="Don't stop Docker after processing")
    parser.add_argument("--config", help="Path to config.yaml")
    args = parser.parse_args()

    processor = TalonProcessor(args.config)

    if args.input_dir:
        processor.originals_dir = Path(args.input_dir)
    if args.output_dir:
        processor.processed_dir = Path(args.output_dir)

    results = processor.process_all_emails(
        start_docker=not args.no_start_docker,
        stop_docker=not args.no_stop_docker
    )

    if results:
        summary = processor.generate_report(results)
        print(f"\nProcessed {summary['successful']}/{summary['total_processed']} emails successfully")
    else:
        print("\nNo emails were processed")
        sys.exit(1)


if __name__ == "__main__":
    main()
