import anyio
import dagger
import json
import requests
import sys
import etcd

etcd_client = etcd.Client()  # TODO: Set host/port


def get_config(name):
    return etcd_client.get(f"/myapp/builds/f{name}")


def approve_rollout():
    payload = {
        'identifier': 'ghcr.io/chakrit/pyconth-2023',
        'action': 'approve',
        'voter': 'chakrit'
    }
    requests.post('https://keel.chakrit.net', data=json.dumps(payload))
    print('build approved')


async def publish_image(client, image):
    addr = get_config('registry_address')
    user = get_config('registry_username')
    pwd = client.set_secret(
        'REGISTRY_PASSWORD',
        get_config('registry_password')
    )

    image = image.with_registry_auth(addr, user, pwd)
    return await image.publish()


def postgres_service(client):
    return (client.container()
            .from_('postgres:15-alpine')
            .with_env_variable('POSTGRES_DB', get_config('db_name'))
            .with_env_variable('POSTGRES_USER', get_config('db_username'))
            .with_env_variable('POSTGRES_PASSWORD', get_config('db_password'))
            .with_exposed_port(5432)
            .as_service()
            )


def djangres_container(client, postgres):
    host = client.host()

    # base image
    djangres = (
        client.container()
        .from_('python:3.11-alpine')
        .with_exec([
            'apk', 'add', '--no-cache',
            'build-base', 'postgresql15-dev'
        ])
        .with_exec(['pip', 'install', 'django', 'django-environ', 'psycopg'])
        .with_service_binding('postgres', postgres)

        .with_env_variable('DB_NAME', 'djangres')
        .with_env_variable('DB_USER', 'djangres')
        .with_env_variable('DB_PASSWORD', 'djangres')
        .with_env_variable('DB_HOST', 'postgres')
        .with_env_variable('DB_PORT', '5432')
        .with_env_variable('DJANGO_SUPERUSER_USERNAME',
                           get_config('superuser_username'))
        .with_env_variable('DJANGO_SUPERUSER_PASSWORD',
                           get_config('superuser_password'))
        .with_env_variable('DJANGO_SUPERUSER_EMAIL',
                           get_config('superuser_email'))

        .with_workdir('/djangres')
        .with_directory('/djangres', host.directory('djangres'))
    )

    # tests
    migration_test = (
        djangres
        .with_env_variable('DB_NAME', get_config('db_name'))
        .with_env_variable('DB_USER', get_config('db_username'))
        .with_env_variable('DB_PASSWORD', get_config('db_password'))
        .with_exec(["python", "manage.py", "migrate"])
        .with_exec(["python", "manage.py", "test"])
    )
    try:
        await migration_test.stdout()
    except dagger.QueryError as e:
        print('migration test failed with', e)
        return

    # final production image
    return (
        djangres.with_new_file("/djangres/entrypoint.sh", contents="""
                       #!/bin/sh
                       python manage.py migrate
                       python manage.py createsuperuser --noinput
                       python manage.py runserver 0.0.0.0:8000
                       """)
        .with_exec(["/bin/sh", "/djangres/entrypoint.sh"])
        .with_exposed_port(8000)
    )


async def main():
    config = dagger.Config(log_output=sys.stderr)
    async with dagger.Connection(config) as client:
        postgres = postgres_service(client)
        await postgres.start()

        djangres = djangres_container(client, postgres)
        image = await publish_image(client, djangres)
        print(f"published {image}")

anyio.run(main)
