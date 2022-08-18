def pytest_addoption(parser):
    """Add options to the `pytest` command"""
    parser.addoption("--use-tokens", action="store_true", default=False, help="Test commands that use environment tokens")
