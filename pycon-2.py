import sys
import anyio
import dagger


async def main():
    config = dagger.Config(log_output=sys.stderr)
    async with dagger.Connection(config) as client:
        host = client.host()

        hello = (
            client.container()
            .from_('alpine:edge')
            .with_file('/hello.py', host.file(__file__))
            .with_exec(['cat', '/hello.py'])
        )

        print(await hello.stdout())

anyio.run(main)
