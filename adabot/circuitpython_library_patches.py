import json
import requests
import os
import shutil
import sh
from sh.contrib import git
from adabot import circuitpython_libraries as adabot_libraries


working_directory = os.path.abspath(os.getcwd())
lib_directory = working_directory + "/.libraries/"
patch_directory = working_directory + "/patches/"
repos = []
check_errors = []
apply_errors = []
stats = []

def get_repo_list():
    repo_list = []
    get_repos = adabot_libraries.list_repos()
    for repo in get_repos:
        if not (repo["owner"]["login"] == "sommersoft" and  # test repos
        #if not (repo["owner"]["login"] == "adafruit" and
                repo["name"].startswith("Adafruit_CircuitPython")):
            continue
        repo_list.append(dict(name=repo["name"], url=repo["clone_url"]))

    return repo_list

def get_patches():
    return_list = []
    #contents = requests.get("https://api.github.com/repos/adafruit/adabot/contents/patches")

    # test contents:
    contents = requests.get("https://api.github.com/repos/sommersoft/adabot/contents/patches?ref=patches")
    if contents.ok:
        for patch in contents.json():
            patch_name = patch["name"]
            return_list.append(patch_name)

    return return_list

def apply_patch(repo_directory, patch_filepath, repo, patch):
    if not os.getcwd() == repo_directory:
        os.chdir(repo_directory)

    try:
        git.am("--signoff", patch_filepath)
    except sh.ErrorReturnCode as Err:
        #print(".. git.am (patch apply) failed")
        apply_errors.append(dict(repo_name=repo,
                               patch_name=patch, error=Err.stderr))
        return False

    try:
        git.push("origin", "adabot_patches") # push to branch during testing
        #git.push()
    except sh.ErrorReturnCode as Err:
        #print(".. Push failed:", Err.stderr)
        apply_errors.append(dict(repo_name=repo,
                               patch_name=patch, error=Err.stderr))
        return False

    return True

def check_patches(repo):
    applied = 0
    skipped = 0
    failed = 0
    patches = get_patches()

    repo_directory = lib_directory + repo["name"]

    for patch in patches:
        #print(". Checking", repo["name"], "for patch:", patch)
        try:
            os.chdir(lib_directory)
        except FileNotFoundError:
            os.mkdir(lib_directory)
            os.chdir(lib_directory)

        try:
            git.clone(repo["url"])
        except sh.ErrorReturnCode_128 as Err:
            if b"already exists" in Err.stderr:
                pass
            else: # erring on the side of caution here
                raise RuntimeError(Err.stderr)
        os.chdir(repo_directory)

        # delete this try block after testing
        try:
            git.checkout("-b", "adabot_patches")
        except sh.ErrorReturnCode as Err:
            if not b'already exists' in Err.stderr:
                raise RuntimeError(Err.stderr)
        # ^^ delete this try block after testing ^^

        patch_filepath = patch_directory + patch
        #print("patch dir:", patch_filepath)
        try:
            git.apply("--check", patch_filepath)
            run_apply = True
        except sh.ErrorReturnCode_1:
            run_apply = False
            #print("..", patch, "Already Applied")
            skipped += 1
        except sh.ErrorReturnCode_128 as Err:
            run_apply = False
            #print(".. Patch check failed")
            failed += 1
            check_errors.append(dict(repo_name=repo["name"],
                               patch_name=patch, error=Err.stderr))

        if run_apply:
            #print(".. Applying Patch To:", repo)
            # this is failing
            result = apply_patch(repo_directory, patch_filepath, repo["name"], patch)
            if result:
                #print("..", patch, "Applied!")
                applied += 1
            else:
                #print("..", patch, "Failed!")
                failed += 1

    return [applied, skipped, failed]

if __name__ == "__main__":
    print(".... Beginning Patch Updates ....")
    print(".... Working directory:", working_directory)
    print(".... Library directory:", lib_directory)
    print(".... Patches directory:", patch_directory)

    check_errors = []
    apply_errors = []
    stats = [0, 0, 0]

    print(".... Deleting any previously cloned libraries")
    libs = os.listdir(path=lib_directory)
    for lib in libs:
        #print("..... Deleting:", lib_directory + lib)
        shutil.rmtree(lib_directory + lib)
        

    repos = get_repo_list()
    run_limit = 5 # delete run_limit after testing
    i = 0 # delete run_limit after testing
    for repo in repos:
        results = check_patches(repo)
        for k in range(len(stats)):
            stats[k] += results[k]
        # delete run_limit after testing
        i += 1
        if i >= run_limit:
            break
        # ^^ delete run_limit after testing ^^

    print(".... Patch Updates Completed ....")
    print(".... Patches Applied:", stats[0])
    print(".... Patches Skipped:", stats[1])
    print(".... Patches Failed:", stats[2], "\n")
    print(".... Patch Check Failure Report ....")
    if len(check_errors) > 0:
        for error, _ in check_errors:
            print(">>", error)
    else:
        print("No Failures")
    print("\n")
    print(".... Patch Apply Failure Report ....")
    if len(apply_errors) > 0:
        for error in apply_errors:
            print(">>", error)
    else:
        print("No Failures")
        
