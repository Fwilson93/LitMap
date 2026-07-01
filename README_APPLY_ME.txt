LitMap Slim layout + stability bundle

Included replacement files:
- app/expand.py
- app/graph.py
- app/main.py
- app/static/app.css
- app/store.py
- app/templates/page.html
- app/templates/partials/project_list.html
- app/templates/partials/workspace.html

What this changes:
- fixes the expansion crash caused by Semantic Scholar sections returning null
- gives the map the centre half of the view with a larger canvas
- keeps projects and new-project controls collapsible on the left rail
- adds delete buttons for existing projects
- moves search + expandable review cards to the right rail
- fixes the search UI to a fixed top-8 result loop
- makes paper nodes and graph links clickable entry points into review

Apply by copying these files into the repository root, preserving paths.

Then run:
  ./run_litmap.sh

Optional verification:
  .venv/bin/python -m pytest -q
