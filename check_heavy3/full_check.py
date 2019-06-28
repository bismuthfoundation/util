import hashlib


def sha256_file(filename):
    """Calculate sha256 hash of file
    """
    buf_size = 65536  # lets read stuff in 64kb chunks!
    sha256 = hashlib.sha256()

    with open(filename, 'rb') as f:
        while True:
            data = f.read(buf_size)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


if __name__ == '__main__':
    print("Checking sha256 of heavy3a.bin file")
    hash = sha256_file("heavy3a.bin")
    if hash != "ffe30d8a63e1731e613b16ff8fd040d2946dba6a09823d7cc09d837570c55199":
        print("Invalid sha256 of file heavy3a.bin. Delete the file and try again.")
    else:
        print("Heavy3a.bin ok")
