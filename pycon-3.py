import sys
import anyio
import dagger

# initialize django app "djanko" with:
#
# 1. django-admin startproject djanko
# 2. adds '0.0.0.0' and 'localhost' to ALLOWED_HOSTS in djanko/settings.py


async def main():
    config = dagger.Config(log_output=sys.stderr)
    async with dagger.Connection(config) as client:
        host = client.host()
        srcdir = host.directory('djanko')

        djanko = (
            client.container()
            .from_('python:3.11-alpine')
            .with_exec(['pip', 'install', 'django'])
            .with_workdir('/djanko')
            .with_mounted_directory('/djanko', srcdir)
            .with_exec(['python', 'manage.py', 'migrate'])
        )

        print(await djanko.stdout())
        await djanko.file('db.sqlite3').export('./djanko/db.sqlite3')

anyio.run(main)
