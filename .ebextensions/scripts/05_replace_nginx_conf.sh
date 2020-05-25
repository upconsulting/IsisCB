if [ "$IS_DOCKER" == "true" ]; then
  echo 'Replacing NGINX configuration...'
  echo "server {\n listen 80 default_server;\nlisten [::]:80 default_server; \nroot /var/www/html; \nserver_name _; \n location / {\ntry_files $uri $uri/ =404;\n } \n}" > /etc/nginx/nginx.conf
else
  echo 'The script 05_replace_nginx_conf.sh is only executed in docker environments.'
fi
