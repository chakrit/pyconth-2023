import sys
import anyio
import dagger

# initialize django app "djangres" with:
#
# 1. django-admin startproject djangres
# 2. set ALLOWED_HOSTS same as in djanko
# 3. adds environ imports
# 3. configure DATABASES entry to read from environment


def postgres_service(client):
    return (client.container()
            .from_('postgres:15-alpine')
            .with_env_variable('POSTGRES_DB', 'workshop')
            .with_env_variable('POSTGRES_USER', 'workshop')
            .with_env_variable('POSTGRES_PASSWORD', 'workshop')
            .with_exposed_port(5432)
            .as_service()
            )


def djangres_service(client, postgres):
    host = client.host()

    return (
        client.container()
        .from_('python:3.11-alpine')
        .with_exec([
            'apk', 'add', '--no-cache',
            'build-base', 'postgresql15-dev'
        ])
        .with_exec(['pip', 'install', 'django', 'django-environ', 'psycopg'])
        .with_service_binding('postgres', postgres)

        .with_env_variable('DB_NAME', 'workshop')
        .with_env_variable('DB_USER', 'workshop')
        .with_env_variable('DB_PASSWORD', 'workshop')
        .with_env_variable('DB_HOST', 'postgres')
        .with_env_variable('DB_PORT', '5432')
        .with_env_variable('DJANGO_SUPERUSER_USERNAME', 'workshop')
        .with_env_variable('DJANGO_SUPERUSER_PASSWORD', 'workshop')
        .with_env_variable('DJANGO_SUPERUSER_EMAIL', 'workshop@example.com')

        .with_workdir('/djangres')
        .with_directory('/djangres', host.directory('djangres'))
        .with_new_file("/djangres/entrypoint.sh", contents="""
                       #!/bin/sh
                       python manage.py migrate
                       python manage.py createsuperuser --noinput
                       python manage.py runserver 0.0.0.0:8000
                       """)
        .with_exec(["/bin/sh", "/djangres/entrypoint.sh"])
        .with_exposed_port(8000)
        .as_service()
    )


async def main():
    config = dagger.Config(log_output=sys.stderr)
    async with dagger.Connection(config) as client:
        postgres = postgres_service(client)
        await postgres.start()

        djangres = djangres_service(client, postgres)
        tunnel = await client.host().tunnel(djangres).start()
        print(f"http://{await tunnel.endpoint()}")

        await anyio.sleep_forever()

anyio.run(main)
