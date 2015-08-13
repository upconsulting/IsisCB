cd /home/ec2-user/isiscb

export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh

workon isiscb

DJANGO_SETTINGS_MODULE="isiscb.development_settings"
export DJANGO_SETTINGS_MODULE

supervisorctl -c /etc/supervisor/conf.d/supervisor.conf start isiscb
