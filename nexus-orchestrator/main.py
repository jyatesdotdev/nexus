# EDUCATIONAL NOTE: The Thinness of This Shim Is the Design
# All real logic lives in the importable `orchestrator` package; this file only
# exists so `python main.py` works from the repo root. Keeping it to a bare
# import + dispatch means there is nothing here that tests, gunicorn, or other
# entry points could accidentally depend on — production serving imports
# orchestrator.asgi directly and never touches this file. If you feel the urge
# to add code here, it almost certainly belongs in orchestrator/cli.py instead.
from orchestrator.cli import cli

if __name__ == "__main__":
    cli()
