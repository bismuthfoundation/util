"""
Hypernode / Bismuth node update script. The script can be run in any directory.
"""

import os
import time
import glob
import tarfile
import requests

def find_all(name, path):
    result = []
    for root, dirs, files in os.walk(path):
        if name in files:
            result.append(os.path.join(root))
    return result

def download_file(url, filename,logsize):
    """From node.py: Download a file from URL to filename
    :param url: URL to download file from
    :param filename: Filename to save downloaded data as
    returns `filename`
    """
    try:
        r = requests.get(url, stream=True)
        total_size = int(r.headers.get('content-length')) / 1024

        with open(filename, 'wb') as filename:
            chunkno = 0
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    chunkno = chunkno + 1
                    if chunkno % logsize == 0:  # every x chunks
                        print("Downloaded {} %".format(int(100 * ((chunkno) / total_size))))

                    filename.write(chunk)
                    filename.flush()
            print("Downloaded 100 %")

        return filename
    except:
        raise

def get_github_latest_release(url):
    r = requests.get(url)
    index = r.text.find('tar.gz')
    index_beg = index
    while r.text[index_beg] != '"': #href separator
       index_beg = index_beg - 1
    path = "https://github.com" + r.text[index_beg+1:index+6]
    return "{}".format(path)

def purge(fileList):
    for filePath in fileList:
        try:
            os.remove(filePath)
        except:
            print("Error while deleting file : ", filePath)


if __name__ == '__main__':
    print("---> Searching for commands.py and cron5.py")
    home = os.path.expanduser("~")
    path1 = find_all('commands.py',home)
    path2 = find_all('cron5.py',home)
    L1 = len(path1)
    L2 = len(path2)

    if (L1 == 1) and (L2 == 1):
        print("commands.py found at: {}".format(path1))
        print("cron5.py found at: {}".format(path2))

        print("---> Getting latest Bismuth node release")
        url = get_github_latest_release("https://github.com/bismuthfoundation/Bismuth/releases")
        print("The latest release version is: " + url)
        answer = input("Do you want to update to this version (y/n): ")
        if answer == "y":
            keep = input("Do you want to keep your existing config.txt (y/n): ")
            download_file(url,"bismuth-latest.tar.gz",1e3)

            print("---> Stopping all screens and temporarily removing cron jobs")
            os.system("crontab -l > my_cron_backup.txt; crontab -r")
            os.system("killall screen")

            if keep == "y":
                print("---> Keeping existing config.txt")
                cmd = "cp {}/config.txt {}/config-keep.txt".format(path1[0],path1[0])
                os.system(cmd)

            print("---> Extracting bismuth-latest.tar.gz file")
            with tarfile.open("bismuth-latest.tar.gz") as tar:
                extract_path = "bis_temp"
                os.mkdir(extract_path)
                tar.extractall(extract_path)
                names = tar.getnames()
                tar_path = names[0]
                cmd = "cp -r {}/{}/* {}; rm -rf {}".format(extract_path,tar_path,path1[0],extract_path)
                os.system(cmd)

            if keep == "y":
                print("---> Keeping existing config.txt")
                cmd = "cp {}/config-keep.txt {}/config.txt; rm {}/config-keep.txt".format(path1[0],path1[0],path1[0])
                os.system(cmd)

            if not os.path.isfile("{}/config_custom.txt"): #Create an empty config_custom.txt if not exists
                file = open("{}/config_custom.txt".format(path1[0]), "w")
                file.close()

            print("---> Downloading verified ledger")
            download_file("https://snapshots.s3.nl-ams.scw.cloud/ledger-verified.tar.gz","ledger-verified.tar.gz",1e5)

            print("---> Removing old ledger files")
            purge(glob.glob(path1[0] + '/static/*.db-shm'))
            purge(glob.glob(path1[0] + '/static/*.db-wal'))
            purge(glob.glob(path1[0] + '/static/ledger*'))
            purge(glob.glob(path1[0] + '/static/hyper*'))
            purge(glob.glob(path1[0] + '/static/*.db'))

            print("---> Extracting ledger-verified.tar.gz file")
            with tarfile.open("ledger-verified.tar.gz") as tar:
                tar.extractall(path1[0] + "/static/")

            print("---> Installing node requirements and starting node.py in screen job")
            cmd = "cd {}; pip3 install -r requirements-node.txt; screen -d -mS node python3 node.py".format(path1[0])
            print(cmd)
            os.system(cmd)

            print("---> Waiting 60 seconds before starting hypernode sentinels")
            time.sleep(60)

            print("---> Restoring hypernode sentinel cron jobs. No need to start the hypernode manually.")
            cmd = "crontab my_cron_backup.txt"
            os.system(cmd)

            print("---> Cleaning up")
            cmd="rm bismuth-latest.tar.gz; rm ledger-verified.tar.gz; rm my_cron_backup.txt"
            os.system(cmd)

    elif (L1 == 0) or (L2 == 0):
        print("node.py or cron5.py not found. Use auto-install script instead: https://github.com/bismuthfoundation/hypernode")
    else:
        print("More than one node.py or cron5.py found, exiting.")
        print(path1)
        print(path2)
