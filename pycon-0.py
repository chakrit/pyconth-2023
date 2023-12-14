import sys
import anyio
import dagger


async def main():
    config = dagger.Config(log_output=sys.stderr)
    async with dagger.Connection(config) as client:
        hello = (
            client.container()
            .from_('alpine:3.19')
            .with_exec(['echo', 'hello'])
        )

        print(await hello.stdout())

anyio.run(main)
