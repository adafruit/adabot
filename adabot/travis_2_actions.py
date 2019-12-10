import subprocess
import os

bashCommand = "ls repositories/"
process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
output, error = process.communicate()

parsed = output.decode('utf8').split('\n')

didnt_do = []
didnt_commit = []
for repo in parsed:
    loc = '/home/dherrada/adafruit/travis_to_actions/repositories/{}/'.format(repo)

    # Tests to see if there's code in the repo

    if not os.path.isfile(loc+'README.rst') and not os.path.isfile(loc+'README.md'):
        didnt_do.append(repo)
        continue

    try:
        with open(loc+'README.rst', 'r') as F:
            if  sum(1 for line in F) < 5:
                didnt_do.append(repo)
                continue
    except FileNotFoundError:
        with open(loc+'README.md', 'r') as F:
            if sum(1 for line in F) < 5:
                didnt_do.append(repo)
                continue

    for root, dirs, files in os.walk(loc):
        for file in files:
            if file.endswith(".py"):
                break
        else:
            continue
        break
    else:
        didnt_do.append(repo)


    os.system('cp -r .github/ {}'.format(loc))

    os.chdir(loc)

    # Makes a branch if there isn't one, usually fails, but that doesn't really matter since os doesn't raise errors for that sort of thing
    os.system('git checkout -b dherrada-patch-1')

    os.system('rm .travis.yml')

    # Removes build* and the resulting blank line from the gitignore
    os.system('sed -i -E "s/build\*//" .gitignore')
    os.system('sed -i /^$/d .gitignore')


    # Switches the badge links from linking to travis to linking to github actions
    os.system("sed -i '/.. image::\|:target:/ s:travis-ci:github: ; s:.com/adafruit/{0}*$:.com/adafruit/{0}/actions/:; s:.svg?branch=master:/workflows/Build%20CI/badge.svg:' README.rst".format(repo))


    os.system("git add .")
    os.system("git diff --cached")
    good = input("Commit?  ")
    if good.lower() == 'y':
        os.system("git commit -m 'Switched from Travis to GitHub Actions'")

    else:
        didnt_commit.append(repo)
    # Commenting this out so I don't accidentally push everything
    # os.system("git push --set-upstream origin dherrada-patch-1")
print(didnt_do)
print(didnt_commit)
