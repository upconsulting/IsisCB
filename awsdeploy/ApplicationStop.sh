cd /home/ec2-user/isiscb

export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

workon isiscb

supervisorctl stop isiscb
supervisorctl shutdown
