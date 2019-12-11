import subprocess
import os
import pickle

def storeData(F, db):
    # initializing data to be stored in db

    dbfile = open(F, 'wb')

    pickle.dump(db, dbfile)
    dbfile.close()

def loadData(F):
    # loading stored data
    dbfile = open(F, 'rb')
    db = pickle.load(dbfile)
    return db

bashCommand = "ls repositories/"
process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
output, error = process.communicate()

parsed = output.decode('utf8').split('\n')

try:
    db = loadData('db.txt')
except EOFError:
    db = {}

for repo in parsed:
    if repo not in db.keys():
        db[repo] = {'didnt do': 0, 'added': 0, 'processed': 0, 'pushed': 0}

    loc = '/home/dherrada/adafruit/travis_to_actions/repositories/{}/'.format(repo)

    # Tests to see if there's code in the repo

    if not os.path.isfile(loc+'README.rst') and not os.path.isfile(loc+'README.md'):
        db[repo]['didnt do'] = 1 
        continue

    try:
        with open(loc+'README.rst', 'r') as F:
            if  sum(1 for line in F) < 5:
                db[repo]['didnt do'] = 1
                continue
    except FileNotFoundError:
        with open(loc+'README.md', 'r') as F:
            if sum(1 for line in F) < 5:
                db[repo]['didnt do'] = 1
                continue

    for root, dirs, files in os.walk(loc):
        for file in files:
            if file.endswith(".py"):
                break
        else:
            continue
        break
    else:
        db[repo]['didnt do'] = 1

    
    if db[repo]['added'] == 0:
        os.system('cp -r .github/ {}'.format(loc))

        os.chdir(loc)

        # Makes a branch if there isn't one, usually fails, but that doesn't really matter since os doesn't raise errors for that sort of thing
        os.system('git checkout -b dherrada-patch-1')

        os.system('rm .travis.yml')

        os.system('git checkout -- .gitignore')
        # Removes build* and the resulting blank line from the gitignore
        os.system('sed -i -E "s/build\*//" .gitignore')
        os.system('sed -i /^$/d .gitignore')

        os.system('git checkout -- README.rst')
        # Switches the badge links from linking to travis to linking to github actions
        os.system("sed -i '/.. image::\|:target:/ s:travis-ci:github: ; s:.com/adafruit/{0}*$:.com/adafruit/{0}/actions/:; s:.svg?branch=master:/workflows/Build%20CI/badge.svg:' README.rst".format(repo))

    if db[repo]['processed'] == 0:
#        if input("would you like to start commiting?  ").lower() != 'y':
#            break
        os.system("git add .")
        db[repo]['added'] = 1
#        os.system("git diff --cached")
#        good = input("Commit?  ")
#        if good.lower() == 'y':
#            os.system("git commit -m 'Switched from Travis to GitHub Actions'")
#            db[repo]['processed'] = 1
    # Commenting this out so I don't accidentally push everything
    # if db[repo]['pushed'] == 0:
        # os.system("git push --set-upstream origin dherrada-patch-1")
        # db[repo]['pushed'] = 1

storeData('db.txt', db)
db = loadData('db.txt')

import csv

with open('repositories.csv', 'a') as csvfile:
    filewriter = csv.writer(csvfile, delimiter=',',
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
    filewriter.writerow(['Name', "Didn't do", 'Added', 'Processed', 'Pushed', 'Link'])

    for k, v in db.items():
        link = 'https://github.com/adafruit/{}'.format(k)
        filewriter.writerow([k, v['didnt do'], v['added'], v['processed'], v['pushed'], link])
