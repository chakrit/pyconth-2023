import sys
import anyio
import dagger

URL = "https://raw.githubusercontent.com/chicolucio/terminal-christmas-tree/master/terminal_tree.py"


async def main():
    config = dagger.Config(log_output=sys.stderr)
    async with dagger.Connection(config) as client:
        hello = (
            client.container()
            .from_('python:3.11-alpine')
            .with_exec(['apk', 'add', '--no-cache', 'curl'])
            .with_exec(['curl', '-o', 'tree.py', URL])
            .with_exec(['python', 'tree.py'])
        )

        print(await hello.stdout())

anyio.run(main)
