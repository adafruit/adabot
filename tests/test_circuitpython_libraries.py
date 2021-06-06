import pytest

from adabot.lib import common_funcs
from adabot import github_requests
from adabot import circuitpython_libraries

def test_circuitpython_libraires(monkeypatch):
    
    def mock_list_repos(*args, **kwargs):
        repos = []
        repos.append(github_requests.get("/repos/adafruit/Adafruit_CircuitPython_TestRepo").json())
        return repos
    
    monkeypatch.setattr(common_funcs, "list_repos", mock_list_repos)

    circuitpython_libraries.main(validator="all")
