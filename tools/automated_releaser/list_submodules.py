import os

drivers = os.listdir("libraries/drivers/")
helpers = os.listdir("libraries/helpers/")

drivers.sort()
helpers.sort()

f = open("drivers.txt", 'w')
for i, submodule in enumerate(drivers):
    if i < len(drivers) -1:
        f.write("{}\n".format(submodule))
    else:
        f.write("{}".format(submodule))
f.close()

f = open("helpers.txt", 'w')
for i, submodule in enumerate(helpers):
    if i < len(helpers) - 1:
        f.write("{}\n".format(submodule))
    else:
        f.write("{}".format(submodule))
f.close()
