import os
import runpy
from unittest.mock import patch

import pytest


@patch.dict(os.environ, {"PORT": "8123"})
@patch("urllib.request.urlopen")
def test_healthcheck_uses_runtime_port_and_timeout(urlopen):
    response = urlopen.return_value
    response.status = 200
    response.read.return_value = b"OK"

    with pytest.raises(SystemExit) as raised:
        runpy.run_path("healthcheck.py", run_name="__main__")

    assert raised.value.code == 0
    urlopen.assert_called_once_with(
        "http://localhost:8123/health",
        timeout=2,
    )
