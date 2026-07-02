LitMap Slim status + queue controls bundle

Included replacement files:
- app/graph.py
- app/main.py
- app/static/app.css
- app/static/app.js
- app/templates/partials/workspace.html

What this changes:
- adds visible working / success / warning / error status feedback
- fixes graph-node clicks so they stay inside the workspace instead of loading the partial route as a whole page
- removes the duplicate scan-map button and keeps one clear map scan action
- compresses accepted / deferred / rejected / queued counts into compact pills
- adds clickable expansion queue items with Add to map and Omit actions
- makes the right rail tabs look more like distinct pages

Apply by copying these files into the repository root, preserving paths.

Then run:
  ./run_litmap.sh

Optional verification:
  .venv/bin/python -m pytest -q
