LitMap Slim interactive workspace fix bundle

Included replacement files:
- app/main.py
- app/templates/partials/workspace.html

What this changes:
- restores clickable search results using a selection panel
- adds Accept / Defer / Reject actions for selected papers
- updates the graph immediately when a paper is accepted
- seeds the expansion queue from accepted papers
- restores a visible map/graph panel and a review/web panel

Apply by copying these files into the repository root, preserving paths.

Then run:
  ./run_litmap.sh

Optional verification:
  .venv/bin/python -m pytest -q
