cd /home/ec2-user/isiscb

# This is necessary for virtualenvwrapper (mkvirtualenv, workon) to work.
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

workon isiscb

INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id);
aws ec2 describe-tags --filters "Name=resource-id,Values="$INSTANCE_ID "Name=key,Values=RDS_USERNAME" > rds_user.json
aws ec2 describe-tags --filters "Name=resource-id,Values="$INSTANCE_ID "Name=key,Values=RDS_PASSWORD" > rds_password.json
aws ec2 describe-tags --filters "Name=resource-id,Values="$INSTANCE_ID "Name=key,Values=AWS_ACCESS_KEY" > rds_access.json
aws ec2 describe-tags --filters "Name=resource-id,Values="$INSTANCE_ID "Name=key,Values=AWS_SECRET_ACCESS_KEY" > rds_secret.json
aws ec2 describe-tags --filters "Name=resource-id,Values="$INSTANCE_ID "Name=key,Values=SOCIAL_AUTH_FACEBOOK_KEY" > facebook_key.json
aws ec2 describe-tags --filters "Name=resource-id,Values="$INSTANCE_ID "Name=key,Values=SOCIAL_AUTH_FACEBOOK_SECRET" > facebook_secret.json
aws ec2 describe-tags --filters "Name=resource-id,Values="$INSTANCE_ID "Name=key,Values=SOCIAL_AUTH_TWITTER_KEY" > twitter_key.json
aws ec2 describe-tags --filters "Name=resource-id,Values="$INSTANCE_ID "Name=key,Values=SOCIAL_AUTH_TWITTER_SECRET" > twitter_secret.json
export RDS_USER=$(python awsdeploy/bin/get_environ.py rds_user.json);
export RDS_PASSWORD=$(python awsdeploy/bin/get_environ.py rds_password.json);
export AWS_ACCESS_KEY=$(python awsdeploy/bin/get_environ.py rds_access.json);
export AWS_SECRET_ACCESS_KEY=$(python awsdeploy/bin/get_environ.py rds_secret.json);
export AWS_SECRET_ACCESS_KEY=$(python awsdeploy/bin/get_environ.py facebook_key.json);
export AWS_SECRET_ACCESS_KEY=$(python awsdeploy/bin/get_environ.py facebook_secret.json);
export AWS_SECRET_ACCESS_KEY=$(python awsdeploy/bin/get_environ.py twitter_key.json);
export AWS_SECRET_ACCESS_KEY=$(python awsdeploy/bin/get_environ.py twitter_secret.json);


# Supervisor manages gunicorn. See awsdeploy/supervisor.conf.
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf start isiscb
