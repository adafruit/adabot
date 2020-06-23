
import os
import shutil
import sh
from sh.contrib import git
from adabot import circuitpython_libraries as adabot_libraries
from adabot import github_requests as github

working_directory = os.path.abspath(os.getcwd())
lib_directory = working_directory + "/.libraries/"

def get_repo_list():
    """ Uses adabot.circuitpython_libraries module to get a list of
        CircuitPython repositories. Filters the list down to adafruit
        owned/sponsored CircuitPython libraries.
    """
    repo_list = []

    get_repos = adabot_libraries.list_repos()
    for repo in get_repos:
        if not (repo["owner"]["login"] == "adafruit" and
                repo["name"].startswith("Adafruit_CircuitPython")):
            continue
        repo_list.append(dict(name=repo["name"], url=repo["clone_url"]))

    return repo_list

def update_branch(repo):
    """ Update the default branch, by first moving the 'master' branch to
        'main', then updating the repo via the GitHub API.
    """

    repo_directory = lib_directory + repo["name"]

    print(f"Updating {repo['name']}:")

    if repo.get("default_branch", "") == "main":
        print("  'main' already default branch")
        return

    try:
        os.chdir(lib_directory)
    except FileNotFoundError:
        os.mkdir(lib_directory)
        os.chdir(lib_directory)

    try:
        git.clone(repo["clone_url"])
    except sh.ErrorReturnCode as err:
        if b"already exists" in err.stderr:
            pass
        else:
            return {"repo": repo["name"], "error": err.stderr}
    os.chdir(repo_directory)

    try:
        git.checkout("master")
    except sh.ErrorReturnCode as err:
        return {"repo": repo["name"], "error": err.stderr}

    try:
        git.branch("-m", "master", "main")
        print("  Branch 'main' created.")
    except sh.ErrorReturnCode as err:
        return {"repo": repo["name"], "error": err.stderr}

    try:
        git.push("-u", "origin", "main")
        print("  'main' branch pushed to GitHub")
    except sh.ErrorReturnCode as err:
        return {"repo": repo["name"], "error": err.stderr}

    patch_result = github.patch(
        "/repos/sommersoft/" + repo["name"],
        json={"default_branch": "main"}
    )
    if not patch_result.ok:
        print("  Failed to update GitHub default branch to 'main'")
        return {
            "repo": repo["name"],
            "error": f"API Returned: <{patch_result.status_code}> {patch_result.text}"
        }
    else:
        print("  GitHub default branch updated to 'main'")

        try:
            git.push("origin", "--delete", "master")
            print("  'master' branch deleted from GitHub")
        except sh.ErrorReturnCode as err:
            return {"repo": repo["name"], "error": err.stderr}

    os.chdir(working_directory)

    return True


if __name__ == "__main__":
    print(".... Beginning Default Branch Changes ....")
    print(".... Working directory:", working_directory)
    print(".... Library directory:", lib_directory)

    errors = []

    print(".... Deleting any previously cloned libraries")
    try:
        libs = os.listdir(path=lib_directory)
        for lib in libs:
            shutil.rmtree(lib_directory + lib)
    except FileNotFoundError:
        pass

    repos = get_repo_list()
    print(".... Updating {} libraries".format(len(repos)))

    successful = 0
    for repo in repos:
        result = update_branch(repo)
        if result:
            if isinstance(result, dict):
                errors.append(result)
            else:
                successful += 1

    print(".... Done!")
    print(".... {} libraries updated".format(successful))
    print(".... Errors:")
    for error in errors:
        print("  > Repo: {0}\n    Error: {1}".format(error["repo"], error["error"]))
