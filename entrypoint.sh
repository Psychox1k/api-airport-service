#!/bin/sh

# Wait for the database to be ready using the script from /usr/local/bin
wait-for-db.sh $POSTGRES_HOST $POSTGRES_PORT

python manage.py migrate
python manage.py collectstatic --noinput
exec python manage.py runserver 0.0.0.0:8000