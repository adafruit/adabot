from jinja2 import Template

def create_release_notes(pypi_name):
    f = open("templates/release_notes_template.md", "r")
    release_notes_template = Template(f.read())
    f.close()

    _rendered_template_text = release_notes_template.render(
        pypi_name=pypi_name
    )

    f = open("release_notes.md", "w")
    f.write(_rendered_template_text)
    f.close()


if __name__ == "__main__":
    #make_issue_description(missing_types=find_missing_annotations("../Adafruit_CircuitPython_ImageLoad/adafruit_imageload"))
    print("")
    create_release_notes("testrepo")
