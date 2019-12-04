import subprocess
import os

bashCommand = "ls repositories/"
process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
output, error = process.communicate()

parsed = output.decode('utf8').split('\n')

for repo in parsed:
    loc = '/home/dherrada/adafruit/travis_to_actions/repositories/{}/'.format(repo)
    os.system('cp -r .github/ repositories/{}/')

    os.chdir(loc)

    # Makes a branch if there isn't one, usually fails, but that doesn't really matter since os doesn't raise errors for that sort of thing
    os.system('git branch -b dherrada-patch-1')

    os.system('git checkout dherrada-patch-1')
 
    os.system('rm .travis.yml')

    # Removes build* and the resulting blank line from the gitignore
    os.system('sed -i -E s/build\*// .gitignore')
    os.system('sed -i /^$/d .gitignore')

    # Switches the badge links from linking to travis to linking to github actions
    os.system("sed  -E -i 's/(.+)(travis-ci)(.+\/adafruit\/Adafruit_CircuitPython_.+)\.svg(.+)/\1github\3\/workflows\/Build%20CI\/badge.svg/; s/(.+target:.+)(travis-ci)(.+)/\1github\3\/actions/' README.rst")

    os.system("git add .")
    os.system("git commit -m 'Switched from Travis to GitHub Actions")
    
    # Commenting this out so I don't accidentally push everything
    # os.system("git push --set-upstream origin dherrada-patch-1")
