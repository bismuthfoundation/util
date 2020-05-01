#!/bin/sh
# This script clones all the repos of the Bismuthfoundation
# usage:
#     sudo apt-get install curl git
#     mkdir archive
#     cd archive
#     wget https://raw.githubusercontent.com/bismuthfoundation/util/master/clone_all.sh
#     chmod u+x clone_all.sh
#     ./clone_all.sh

CNTX={orgs}; NAME={Bismuthfoundation}; PAGE=1
curl "https://api.github.com/$CNTX/$NAME/repos?page=$PAGE&per_page=100" |
  grep -e 'git_url*' |
  cut -d \" -f 4 |
  xargs -L1 git clone
