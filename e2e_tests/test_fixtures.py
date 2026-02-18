"""
Test runner for fixture emails.
Processes HTML email fixtures through talon-web API and reports results.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import requests
import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
QUOTEQUAIL_DIR = FIXTURES_DIR / "quotequail"
O365_DIR = FIXTURES_DIR


class FixtureTester:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.extract_endpoint = f"{base_url}/reply/extract_from_html"
        self.health_endpoint = f"{base_url}/health"

    def check_health(self) -> bool:
        """Check if talon-web is running."""
        try:
            resp = requests.get(self.health_endpoint, timeout=5)
            return resp.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def load_fixture(self, filepath: Path) -> str:
        """Load HTML fixture file."""
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def process_fixture(self, filepath: Path) -> Dict:
        """Process a single fixture through talon-web."""
        html = self.load_fixture(filepath)
        
        try:
            resp = requests.post(
                self.extract_endpoint,
                data=html.encode("utf-8"),
                headers={"Content-Type": "text/html"},
                timeout=30
            )
            result = resp.json()
            result["status_code"] = resp.status_code
            result["success"] = resp.status_code == 200
        except requests.exceptions.RequestException as e:
            result = {
                "success": False,
                "error": str(e),
                "status_code": 0
            }
        except json.JSONDecodeError:
            result = {
                "success": False,
                "error": "Invalid JSON response",
                "status_code": resp.status_code if 'resp' in locals() else 0
            }
        
        return result

    def run_tests(self) -> Dict:
        """Run tests on all fixtures."""
        results = {
            "fixtures_tested": 0,
            "successful": 0,
            "failed": 0,
            "by_client": {},
            "results": []
        }

        if not self.check_health():
            logger.error(f"Cannot connect to talon-web at {self.base_url}")
            logger.info("Make sure talon-web is running: python app.py or gunicorn app:app")
            return results

        logger.info(f"Testing fixtures from {FIXTURES_DIR}")

        # Test quotequail fixtures
        if QUOTEQUAIL_DIR.exists():
            logger.info(f"\n=== Quotequail Fixtures ===")
            for fixture_file in sorted(QUOTEQUAIL_DIR.glob("*.html")):
                client_name = fixture_file.stem.rsplit("_", 1)[0]  # e.g., gmail from gmail_reply
                logger.info(f"Testing: {fixture_file.name}")
                
                result = self.process_fixture(fixture_file)
                result["fixture_file"] = str(fixture_file.relative_to(FIXTURES_DIR))
                result["client"] = client_name
                
                results["results"].append(result)
                results["fixtures_tested"] += 1
                
                if result["success"]:
                    results["successful"] += 1
                    extracted_len = len(result.get("text", ""))
                    logger.info(f"  ✓ Success - extracted {extracted_len} chars")
                else:
                    results["failed"] += 1
                    logger.error(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

                if client_name not in results["by_client"]:
                    results["by_client"][client_name] = {"tested": 0, "passed": 0}
                results["by_client"][client_name]["tested"] += 1
                if result["success"]:
                    results["by_client"][client_name]["passed"] += 1

        # Test O365 fixtures (if any added)
        o365_fixtures = [f for f in FIXTURES_DIR.glob("o365_*.html")]
        if o365_fixtures:
            logger.info(f"\n=== O365 Fixtures ===")
            for fixture_file in sorted(o365_fixtures):
                logger.info(f"Testing: {fixture_file.name}")
                
                result = self.process_fixture(fixture_file)
                result["fixture_file"] = str(fixture_file.relative_to(FIXTURES_DIR))
                result["client"] = "o365"
                
                results["results"].append(result)
                results["fixtures_tested"] += 1
                
                if result["success"]:
                    results["successful"] += 1
                    extracted_len = len(result.get("text", ""))
                    logger.info(f"  ✓ Success - extracted {extracted_len} chars")
                else:
                    results["failed"] += 1
                    logger.error(f"  ✗ Failed: {result.get('error', 'Unknown error')}")

                if "o365" not in results["by_client"]:
                    results["by_client"]["o365"] = {"tested": 0, "passed": 0}
                results["by_client"]["o365"]["tested"] += 1
                if result["success"]:
                    results["by_client"]["o365"]["passed"] += 1

        return results

    def print_summary(self, results: Dict):
        """Print test summary."""
        logger.info(f"\n{'='*50}")
        logger.info(f"TEST SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Total fixtures tested: {results['fixtures_tested']}")
        logger.info(f"Successful: {results['successful']}")
        logger.info(f"Failed: {results['failed']}")
        
        if results['by_client']:
            logger.info(f"\nBy client:")
            for client, stats in results["by_client"].items():
                status = "✓" if stats["tested"] == stats["passed"] else "✗"
                logger.info(f"  {status} {client}: {stats['passed']}/{stats['tested']} passed")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test fixture emails against talon-web")
    parser.add_argument("--url", default="http://localhost:5000", help="Base URL for talon-web")
    parser.add_argument("--output", help="Output JSON file for results")
    args = parser.parse_args()

    tester = FixtureTester(base_url=args.url)
    results = tester.run_tests()
    tester.print_summary(results)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"\nResults saved to {output_path}")
    
    # Exit with error code if any tests failed
    sys.exit(0 if results["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
