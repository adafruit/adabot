import json
import requests
import os
import sh
from sh.contrib import git
from adabot import circuitpython_bundle as adabot_bundle
from adabot import circuitpython_libraries as adabot_libraries
from adabot import github_requests as github

working_directory = os.path.abspath(os.getcwd())

repos = [repo["name"] for repo in adabot_libraries.list_repos()]
#repos = ["Adafruit_CircuitPython_ADS1x15", "Adafruit_CircuitPython_AM2320"]

def get_patches():
    return_list = []
    #contents = requests.get("https://api.github.com/repos/adafruit/adabot/contents/adabot")

    # test contents:
    contents = requests.get("https://api.github.com/repos/sommersoft/adabot/contents/patches")
    print(contents.text)
    if contents.ok:
        #patches = [files["name"] for files in contents.json()]
        print(json.dumps(contents.json(), indent=2), "\n")
        for patch in contents.json():
            patch_name = patch["name"]
            return_list.append(patch_name)

    return return_list

def check_patches():
    patches = get_patches()
    #print(patches, "\n")

    #working_directory = os.path.abspath(os.getcwd())
    patch_directory = working_directory + "/patches/"
    for repo in repos:
        for patch in patches:
            print("Checking", repo, "for patch:", patch)
            os.chdir("../" + repo)
            print("repo dir:", os.getcwd())
            patch_filepath = patch_directory + patch
            print("patch dir:", patch_filepath)
            try:
                git.apply("--check", "--verbose", patch_filepath)
                r = True
            except sh.ErrorReturnCode_1:
                r = False
                print("Already Applied", "\n")
            except sh.ErrorReturnCode_128:
                r = False
                print("Errored", "\n")

            if r:
            #    git.am("--signoff", patch_filepath)
                print("Applying Patch...", "\n")


if __name__ == "__main__":
    print(".... Beginning Patch Updates ....\n")
    print("Working directory:", working_directory)
    os.chdir("..")
    directory = os.path.abspath(".bundles")
    print("Bundles directory:", directory)
    #for bundle in adabot_bundle.bundles:
    #    bundle_path = os.path.join(directory, bundle)
    #    try:
    #        fetch_bundle(bundle, bundle_path)

    check_patches()
