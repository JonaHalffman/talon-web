import os
import urllib.request

port = os.getenv("PORT", "5000")
response = urllib.request.urlopen(
    f"http://localhost:{port}/health",
    timeout=2,
)

if response.status != 200:
    exit(1)

if response.read().decode("utf8") != "OK":
    exit(1)

exit(0)
