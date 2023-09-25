# Automated GitHub Release Maker

## Requirements

- git
- gh (github CLI)
- Python
- toml python library
- Jinja2 python library

To run the release automation:

First set the `RELEASE_TITLE` variable inside of `release_maker_scripts/make_release.py` to something appropriate for the new release.

Then run:
```
git submodule foreach "python ../../../copy_release_making_files.py;python run_on_each.py"
```

You can redirect the output to a log file like this:
```
git submodule foreach "python ../../../copy_release_making_files.py;python run_on_each.py" > automation_log.txt
```

## Notes

Scripts and instructions are written to assume Python3 is installed and accessible to all users with the `python`.

If you run `python` and do not see the Python 3 REPL then you need to:

1. Install Python3
2. If necessary, Make a symbolic link or shortcut that allows `python` to point to `python3`

Use a virtual environment if you are in a context where Python 2 exists so that inside your venv `python` will point to the venv rather than the systedm Py2.

## Steps to run on subset:

1. Clone the library bundle and download all submodules. `clone_bundle.sh` can be used for this
2. Copy the following files / folders into the root of the bundle:
   - `release_maker_scripts/`
   - `copy_release_making_files.py`
   - `list_submodules.py`
   - `remove_submodules.py`
3. Run `list_submodules.py` it will create `drivers.txt` and `helpers.txt`
4. Delete / Remove any libraries you want _**included**_ in the subset from these files. i.e. (if you want to run on only `acep7in` and `adxl34x` then delete those two lines from the drivers.txt file and leave all other lines). _**Ensure there are no blank lines in either txt file!**_
5. Run `remove_submodules.py` it will remove all library submodules that are present in `drivers.txt` and `helpers.txt` (any libraries not in those files will remain intact)
6. Run `git submodule foreach "python ../../../copy_release_making_files.py;python run_on_each.py"`

To run it against the rest of the full set (without duplicates). Repeat the above process, but remove all except the libraries completed from the txt files.
