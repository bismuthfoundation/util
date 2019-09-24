"""
Hypernode / Bismuth node update script. The script can be run in any directory.
"""

import os
import sys
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

def download_file(url, filename, logsize):
    """From node.py: Download a file from URL to filename
    :param url: URL to download file from
    :param filename: Filename to save downloaded data as
    :param logsize: Download status display frequency
    returns `filename`
    """

    bOK = False
    while not bOK:
        try:
            r = requests.get(url, stream=True)
            total_size = int(r.headers.get('content-length')) / 1024
            bOK = True
        except:
            print("---> Contacting https://github.com again")
            bOK = False
            time.sleep(10)

    try:
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
    path = "https://github.com" + "{}".format(r.text[index_beg+1:index+6])
    return path

def purge(fileList):
    for filePath in fileList:
        try:
            os.remove(filePath)
        except:
            print("Error while deleting file : ", filePath)

def search_and_replace_in_file(filename,search,replace):
    try:
        with open(filename, 'r') as file:
            filedata = file.read()
        # Replace the target string
        filedata = filedata.replace(search, replace)
        # Write the file out again
        with open(filename, 'w') as file:
            file.write(filedata)
    except:
        print("File {} does not exist".format(filename))

if __name__ == '__main__':
    print("---> Checking for Python 3.7")
    try:
        assert sys.version_info >= (3, 7)
    except:
        print("This update script requires Python 3.7")
        print("Before continuing, do the following as root:")
        print("apt update")
        print("apt install python3.7-dev libmp3-dev python3-pip")
        print("After installation, run this script with: python3.7 hn_node_update.py")
        sys.exit()

    print("----------")
    print("apt update")
    print("apt install python3.7-dev libmp3-dev python3-pip")
    print("----------")
    answer = input("Did you run the above commands as root (y/n): ")
    if answer is not "y":
        sys.exit()

    print("---> Searching for commands.py and cron5.py")
    home = os.path.expanduser("~")
    path1 = find_all('commands.py',home)
    path2 = find_all('cron5.py',home)
    L1 = len(path1)
    L2 = len(path2)

    if (L1 == 1) and (L2 == 1):
        print("commands.py found at: {}".format(path1))
        print("cron5.py found at: {}".format(path2))

        i = path2[0].find('/crontab')
        hn_path = path2[0][0:i] # Main folder of hypernode

        print("---> Getting latest Bismuth node release")
        url = get_github_latest_release("https://github.com/bismuthfoundation/Bismuth/releases")
        print("The latest release version is: " + url)
        answer = input("Do you want to update to this version (y/n): ")
        if answer == "y":
            #keep = input("Do you want to keep your existing config.txt (y/n). If not sure, answer n: ")
            keep = "n"
            download_file(url,"bismuth-latest.tar.gz",1e3)

            print("---> Stopping all screens and temporarily removing cron jobs")
            os.system("crontab -l > my_cron_backup.txt; crontab -r")
            os.system("killall screen")

            if keep == "y":
                print("---> Keeping existing config.txt")
                cmd = "cp {}/config.txt {}/config-keep.txt".format(path1[0],path1[0])
                os.system(cmd)

            if keep == "n":
                print("---> Creating backup of existing config.txt")
                cmd = "cp {}/config.txt {}/config-backup.txt".format(path1[0],path1[0])
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

            print("Installing/updating plugins")
            cmd = "cd {}; cd plugins; mkdir 035_socket_client; cd 035_socket_client; rm __init__.py; wget https://github.com/bismuthfoundation/BismuthPlugins/raw/master/plugins/035_socket_client/__init__.py".format(path1[0])
            os.system(cmd)
            cmd = "cd {}; cd plugins/500_hypernode; rm __init__.py; wget https://github.com/bismuthfoundation/hypernode/raw/beta99/node_plugin/__init__.py".format(path1[0])
            os.system(cmd)
            cmd = "cd {}; rm ledger_queries.py; wget https://github.com/bismuthfoundation/hypernode/raw/beta99/node_plugin/ledger_queries.py".format(path1[0])
            os.system(cmd)

            print("---> Downloading verified ledger")
            download_file("http://212.47.253.89/ledger-verified.tar.gz","ledger-verified.tar.gz",1e5)

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
            cmd = "cd {}; rm -rd polysign; python3.7 -m pip install -r requirements-node.txt; python3.7 -m pip install ipwhois fastecdsa; screen -d -mS node python3.7 node.py".format(path1[0])
            os.system(cmd)

            print("---> Updating Hypernode files to beta99")
            cmd = "cd {}".format(hn_path)
            url="https://github.com/bismuthfoundation/hypernode/archive/beta99.tar.gz"
            download_file(url,"hn-latest.tar.gz",1e3)
            with tarfile.open("hn-latest.tar.gz") as tar:
                extract_path = "hn_temp"
                os.mkdir(extract_path)
                tar.extractall(extract_path)
                names = tar.getnames()
                tar_path = names[0]
                cmd = "cp -r {}/{}/* {}; rm -rf {}".format(extract_path,tar_path,hn_path,extract_path)
                os.system(cmd)

            print("---> Installing Hypernode requirements")
            cmd = "cd {}; python3.7 -m pip install -r requirements.txt".format(hn_path)
            os.system(cmd)

            print("---> Changing 'python3' to 'python3.7' in cron1.py")
            filename = "{}/cron1.py".format(path2[0])
            search_and_replace_in_file(filename, "'python3'","'python3.7'")

            print("---> Changing 'python3' to 'python3.7' in sentinel.py")
            filename = "{}/sentinel/sentinel.py".format(hn_path)
            search_and_replace_in_file(filename, "'python3'","'python3.7'")

            print("---> Changing 'python3' to 'python3.7' in old sentinel if it exists")
            filename = "{}/node_sentinel.py".format(path1[0])
            search_and_replace_in_file(filename, "'python3'","'python3.7'")

            print("---> Deleting existing poschain to enable bootstrap")
            cmd = "cd {}/main/data; rm *".format(hn_path)
            os.system(cmd)

            print("---> Waiting 60 seconds before restoring cron jobs")
            time.sleep(60)

            print("---> Search-and-replace of Python3 to Python3.7")
            search_and_replace_in_file('my_cron_backup.txt', 'python3 ','python3.7 ')

            print("---> Restoring hypernode sentinel cron jobs. No need to start the hypernode manually.")
            cmd = "crontab my_cron_backup.txt"
            os.system(cmd)

            print("---> Cleaning up")
            cmd="rm bismuth-latest.tar.gz; rm ledger-verified.tar.gz; rm my_cron_backup.txt; rm hn-latest.tar.gz"
            os.system(cmd)

    elif (L1 == 0) or (L2 == 0):
        print("commands.py or cron5.py not found. Use auto-install script instead: https://github.com/bismuthfoundation/hypernode")
    else:
        print("More than one commands.py or cron5.py found, exiting.")
        print(path1)
        print(path2)
