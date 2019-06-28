import os


if __name__ == '__main__':
    print("Checking file size of heavy3a.bin file")
    size = os.path.getsize("heavy3a.bin")
    if size != 1073741824:
        print("Invalid size of file heavy3a.bin. Delete the file and try again.")
    else:
        print("Heavy3a.bin size ok")

