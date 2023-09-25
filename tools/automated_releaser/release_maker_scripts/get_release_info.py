import subprocess



def get_release_info():
    #result = subprocess.check_output(['gh', 'release', 'list', '-L', '1', '|', 'awk', '2'])
    result = subprocess.getoutput("gh release list -L 1 | awk 2")
    createdAt = result.split('\t')[-1]
    tag = result.split('\t')[-2]


    tag_parts = tag.split(".")

    tag_parts[-1] = str(int(tag_parts[-1]) + 1)

    new_tag = ".".join(tag_parts)


    # print("Latest release is:")
    # print(f"tag: {tag}")
    # print(f"createdAt: {createdAt}")
    # print(f"new tag: {new_tag}")

    return {
        "current_tag": tag,
        "new_tag": new_tag,
        "created_at": createdAt
    }