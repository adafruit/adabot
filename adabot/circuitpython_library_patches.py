import json
import requests
import os
import sys
import getopt
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

help_list = (".... Adabot CircuitPython Library Patch Help ...." + "\n\n" +
    "-l, --list: Lists the available pathces to run." + "\n\n" +
    "-p=<name>, --patch=<name>: runs only the single patch referenced." + "\n\n" +
    "-f=[flags], --flags=[flags]: adds the referenced list of flags to "
    "the git.am call when running a single patch. '-p' option must be used.")

def get_repo_list():
    """ Uses adabot.circuitpython_libraries module to get a list of
        CircuitPython repositories. Filters the list down to adafruit
        owned/sponsored CircuitPython libraries.
    """
    repo_list = []
    get_repos = adabot_libraries.list_repos()
    for repo in get_repos:
        #if not (repo["owner"]["login"] == "adafruit" and
        if not (repo["owner"]["login"] == "sommersoft" and
                repo["name"].startswith("Adafruit_CircuitPython")):
            continue
        repo_list.append(dict(name=repo["name"], url=repo["clone_url"]))

    return repo_list

def get_patches():
    """ Returns the list of patch files located in the adabot/patches
        directory.
    """
    return_list = []
    contents = requests.get("https://api.github.com/repos/adafruit/adabot/contents/patches")

    if contents.ok:
        for patch in contents.json():
            patch_name = patch["name"]
            return_list.append(patch_name)

    return return_list

def apply_patch(repo_directory, patch_filepath, repo, patch, flags):
    """ Apply the `patch` in `patch_filepath` to the `repo` in
        `repo_directory` using git am. --signoff will sign the commit
        with the user running the script (adabot if credentials are set
        for that).
    """
    if not os.getcwd() == repo_directory:
        os.chdir(repo_directory)

    try:
        am_flags = ["--signoff"]
        am_flags.extend(flags)
        git.am(am_flags, patch_filepath)
    except sh.ErrorReturnCode as Err:
        apply_errors.append(dict(repo_name=repo,
                                 patch_name=patch, error=Err.stderr))
        return False

    try:
        git.push()
    except sh.ErrorReturnCode as Err:
        apply_errors.append(dict(repo_name=repo,
                                 patch_name=patch, error=Err.stderr))
        return False

    return True

def check_patches(repo, patches, flags):
    """ Gather a list of patches from the `adabot/patches` directory
        on the adabot repo. Clone the `repo` and run git apply --check
        to test wether it requires any of the gathered patches.
    """
    applied = 0
    skipped = 0
    failed = 0
  
    repo_directory = lib_directory + repo["name"]

    for patch in patches:
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
            else:
                raise RuntimeError(Err.stderr)
        os.chdir(repo_directory)

        patch_filepath = patch_directory + patch

        try:
            git.apply("--check", patch_filepath)
            run_apply = True
        except sh.ErrorReturnCode_1 as Err:
            run_apply = False
            if not b"error" in Err.stderr:
                skipped += 1
            else:
                failed += 1
                check_errors.append(dict(repo_name=repo["name"],
                                         patch_name=patch, error=Err.stderr))
            
        except sh.ErrorReturnCode as Err:
            run_apply = False
            failed += 1
            check_errors.append(dict(repo_name=repo["name"],
                                     patch_name=patch, error=Err.stderr))

        if run_apply:
            result = apply_patch(repo_directory, patch_filepath, repo["name"], patch, flags)
            if result:
                applied += 1
            else:
                failed += 1

    return [applied, skipped, failed]

def cmd_line_handler(argv):
    which_patches = get_patches()
    flags = []
    try:
        opts, args = getopt.getopt(argv, "hlp:f:", ["help", "list", "patch=", "flags="])
    except getopt.GetoptError:
        raise ValueError("Argument(s) invalid.")

    print(opts, args)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            flags = "help"
            break
        if opt in ("-l", "--list"):
            flags = "list"
            break
        if opt in ("-p", "--patch"):
            if not arg in which_patches:
                msg = ("'" + arg + "' file not in repository. Submit Pull Request with new"
                       " patch file before re-trying.")
                raise ValueError(msg)
            else:
                which_patches = [arg]
        elif opt in ("-f", "--flags"):
            print([p[0] for p in opts])
            if not "-p" in [p[0] for p in opts]:
                raise ValueError("Patch file must be supplied to use flags.")
            for flag in arg:
                if (flag == "i"):
                    raise ValueError('Interactive mode not available.')
                flags.append(flag)

    return which_patches, flags

if __name__ == "__main__":

    patches, flags = cmd_line_handler(sys.argv[1:])
    print(patches)
    if (flags == "help"):
        print(help_list)
        sys.exit()
    if (flags == "list"):
        print(".... Pathces Available To Run:", patches)
        sys.exit()

    print(".... Beginning Patch Updates ....")
    print(".... Working directory:", working_directory)
    print(".... Library directory:", lib_directory)
    print(".... Patches directory:", patch_directory)

    check_errors = []
    apply_errors = []
    stats = [0, 0, 0]

    print(".... Deleting any previously cloned libraries")
    try:
        libs = os.listdir(path=lib_directory)
        for lib in libs:
            shutil.rmtree(lib_directory + lib)
    except FileNotFoundError:
        pass    

    repos = get_repo_list()
    print(".... Running Patch Checks On", len(repos), "Repos ....")

    i = 0
    for repo in repos:
        results = check_patches(repo, patches, flags)
        for k in range(3):
           stats[k] += results[k]
        i += 1
        if (i > 5):
            break

    print(".... Patch Updates Completed ....")
    print(".... Patches Applied:", stats[0])
    print(".... Patches Skipped:", stats[1])
    print(".... Patches Failed:", stats[2], "\n")
    print(".... Patch Check Failure Report ....")
    if len(check_errors) > 0:
        for error in check_errors:
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
        
