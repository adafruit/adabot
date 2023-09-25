import subprocess
import toml


def get_pypi_name():
    #result = subprocess.check_output(['gh', 'release', 'list', '-L', '1', '|', 'awk', '2'])

    # full_repo_name = subprocess.getoutput("pwd").split("/")[-1]
    # lib_shortname = full_repo_name.split("Adafruit_CircuitPython_")[1]
    # lib_pypiname = lib_shortname.replace("_", "-").lower()

    data = toml.load("pyproject.toml")

    return data['project']['name'].replace("adafruit-circuitpython-", "")