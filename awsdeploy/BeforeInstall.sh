mkvirtualenv isiscb
workon isiscb

pip install -r requirements.txt

chmod u+x bin/gunicorn_start
touch ../logs/gunicorn_supervisor.log

sudo supervisorctl reread
sudo supervisorctl update
