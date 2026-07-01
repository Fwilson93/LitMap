LitMap Slim speed + tabbed rails bundle

Included replacement files:
- app/graph.py
- app/main.py
- app/models.py
- app/static/app.css
- app/static/app.js
- app/templates/partials/workspace.html

What this changes:
- removes the forced smooth-scroll after every HTMX swap
- separates search, PDF ingress/retrieval, and expansion queue into tabs on the right rail
- removes extra functionality panels from below the search results and below the map
- adds a dedicated "Scan map for expansion suggestions" action
- makes Accept/Reject/Defer faster by no longer running expansion automatically during node add
- limits review to the current visible search result set while keeping cached candidates in the project

Apply by copying these files into the repository root, preserving paths.

Then run:
  ./run_litmap.sh

Optional verification:
  .venv/bin/python -m pytest -q
