cd /home/ec2-user/isiscb

# This is necessary for virtualenvwrapper (mkvirtualenv, workon) to work.
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

workon isiscb
touch /home/ec2-user/isiscb/isiscb/server_start
chmod 666 /home/ec2-user/isiscb/isiscb/server_start

INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id);
aws ec2 describe-tags --filters "Name=resource-id,Values=i-a5accd63" "Name=key,Values=RDS_USER" > rds_user.json
aws ec2 describe-tags --filters "Name=resource-id,Values=i-a5accd63" "Name=key,Values=RDS_PASSWORD" > rds_password.json
export RDS_USER=$(python awsdeploy/bin/get_environ.py rds_user.json);
export RDS_PASSWORD=$(python awsdeploy/bin/get_environ.py rds_password.json);

# Supervisor manages gunicorn. See awsdeploy/supervisor.conf.
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf start isiscb
