cd /home/ec2-user/isiscb

# This is necessary for virtualenvwrapper (mkvirtualenv, workon) to work.
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

# Select the development configuration. See development_settings.py.
DJANGO_SETTINGS_MODULE="isiscb.development_settings"
export DJANGO_SETTINGS_MODULE

mkvirtualenv isiscb
workon isiscb

# Install (new) Python dependencies.
pip install -r requirements.txt

# Populate environment variables from EC2 instance tags.
INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id);
aws ec2 describe-tags --filters "Name=resource-id,Values=i-a5accd63" "Name=key,Values=RDS_USER" > rds_user.json
aws ec2 describe-tags --filters "Name=resource-id,Values=i-a5accd63" "Name=key,Values=RDS_PASSWORD" > rds_password.json
aws ec2 describe-tags --filters "Name=resource-id,Values=i-a5accd63" "Name=key,Values=AWS_ACCESS_KEY" > rds_access.json
aws ec2 describe-tags --filters "Name=resource-id,Values=i-a5accd63" "Name=key,Values=AWS_SECRET_ACCESS_KEY" > rds_secret.json
export RDS_USER=$(python awsdeploy/bin/get_environ.py rds_user.json);
export RDS_PASSWORD=$(python awsdeploy/bin/get_environ.py rds_password.json);
export AWS_ACCESS_KEY=$(python awsdeploy/bin/get_environ.py rds_access.json);
export AWS_SECRET_ACCESS_KEY=$(python awsdeploy/bin/get_environ.py rds_secret.json);


# Supervisor manages Gunicorn, and perhaps other services down the road.
#  supervisor.conf is updated (overwritten) on each deploy, so this loads
#  the new configuration.
supervisord -c /etc/supervisor/conf.d/supervisor.conf
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf reread
supervisorctl -c /etc/supervisor/conf.d/supervisor.conf update

# Static files are hosted on S3. This will push any new or updated static files
#  to the appropriate bucket (see development_settings.py).
cd isiscb
python manage.py collectstatic --noinput
python manage.py migrate
