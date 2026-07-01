LitMap Slim safe compatibility fix bundle

Included replacement files:
- app/main.py
- app/models.py
- app/search.py
- app/store.py
- app/templates/partials/workspace.html

Copy these files into the repository root, preserving paths.
Then run:
  ./run_litmap.sh

Optional verification:
  .venv/bin/python -m pytest -q
