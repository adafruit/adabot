import pickle
from subprocess import check_output
import os


def storeData(F, db):
    # Stores data in db file
    dbfile = open(F, 'wb')
    pickle.dump(db, dbfile)
    dbfile.close()


def loadData(F):
    # Loads data from db file
    dbfile = open(F, 'rb')
    db = pickle.load(dbfile)
    return db


dirlist = check_output('ls repositories/', shell=1).decode('utf-8').split('\n')
dirlist.pop()

try:
    db = loadData('db.txt')
except EOFError:
    db = {}

for repo in dirlist:
    if repo not in db.keys():
        db[repo] = {'didnt do': 0, 'added': 0, 'processed': 0, 'pushed': 0}

    loc = '/home/dherrada/travis_to_actions/repositories/{}/'.format(repo)

    for root, dirs, files in os.walk(loc):
        for file in files:
            if file.endswith(".py"):
                break
        else:
            continue
        break
    else:
        db[repo]['didnt do'] = 1
        print('no .py')

    if db[repo]['didnt do'] == 1:
        print('didnt do')
        continue

    if db[repo]['added'] == 0:
        os.system('cp -r .github/ {}'.format(loc))

        os.chdir(loc)

        os.system('git checkout -b dherrada-patch-1')

        os.system('rm .travis.yml')

        os.system('git checkout -- .gitignore')

        os.system('sed -i -E "s/build\*//" .gitignore')
        os.system('sed -i /^$/d .gitignore')

    if db[repo]['processed'] == 0:
        # Switches the badge links from linking to travis to linking to github actions
        os.system("sed -i '/.. image::\|:target:/ s:travis-ci:github: ; s:.com/adafruit/{0}*$:.com/adafruit/{0}/actions/:; s:.svg?branch=master:/workflows/Build%20CI/badge.svg:' README.rst".format(repo))

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


os.chdir('/home/dherrada/travis_to_actions/')
storeData('db.txt', db)

with open('repositories.csv', 'w') as F:
    F.write('Name, Didn\'t do, Added, Processed, Pushed\n')
    for k, v in db.items():
        link = 'https://github.com/adafruit/{}'.format(k)
        line = str(k)+','+str(v['didnt do'])+','+str(v['added'])+','+str(v['processed'])+','+str(v['pushed'])+','+link+'\n'
        F.write(line)
