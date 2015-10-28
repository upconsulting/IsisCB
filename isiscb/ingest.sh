while read p; do
  python manage.py loaddata $p
done <isisdata/fixtures/fm_fixtures5.txt
