while read p; do
  python manage.py loaddata $p
done <isisdata/fixtures/fm_fixtures6.txt
