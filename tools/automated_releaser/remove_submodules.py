import os

f = open("drivers.txt", "r")
drivers = f.read().split("\n")
f.close()

f = open("helpers.txt", "r")
helpers = f.read().split("\n")
f.close()

print(drivers)
print(helpers)

for driver in drivers:
    os.system("git submodule deinit -f libraries/drivers/{}/".format(driver))

for helper in helpers:
    os.system("git submodule deinit -f libraries/helpers/{}/".format(helper))
