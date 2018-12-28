# Go here to generate a github access token:
#  https://help.github.com/articles/creating-a-personal-access-token-for-the-command-line/
# KEEP THIS TOKEN SECRET AND SAFE! Anyone with access to the token has FULL CONTROL of your GitHub account!
export ADABOT_GITHUB_ACCESS_TOKEN=<your personal access token>
# Go here to generate a travis access token:
#  https://blog.travis-ci.com/2013-01-28-token-token-token
# Note you want the 'Travis Token' (third option) and NOT the 'Access Token'.  Use the ruby gem mentioned to generate.
# KEEP THIS TOKEN SECRET AND SAFE! Although it is unclear what access the token grants (Travis seems to imply it's less
# risk to share), always assume secrets like these are dangerous to expose to others.
# Note 2: since all CircuitPython repositories have been migragted to travis-ci.com, be sure to use an access token
# from '.com', not '.org'. These tokens are not interchangeable.
export ADABOT_TRAVIS_ACCESS_TOKEN=<your Travis token>
