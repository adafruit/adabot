import pytest

from adabot import arduino_libraries
from adabot import github_requests

def test_adafruit_libraries(monkeypatch):

    def get_list_repos():
        repos = []
        repos.append(github_requests.get("/repos/adafruit/Adafruit_NeoPixel").json())
        return repos

    monkeypatch.setattr(arduino_libraries, "list_repos", get_list_repos)

    print(arduino_libraries.list_repos())

    arduino_libraries.main()