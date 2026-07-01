# Project intent

## Goal

Keep LitMap Slim focused on a local-first literature exploration loop:

1. search literature metadata
2. review candidates in a browser workspace
3. record yes / no / defer decisions
4. grow a controlled literature graph from accepted items
5. expand the graph via:
   - citations (forward and backward)
   - author relationships
   - related topics/papers
6. manage an expansion queue where:
   - candidates must be explicitly accepted
   - ignored items may reappear
   - blacklisted items never reappear
7. retrieve PDFs and supplementary material
8. track local file availability
9. export accepted literature into a LitCap-style handoff directory

## Key system distinctions

### Search vs Expansion
- search = user-initiated discovery
- expansion = graph-driven candidate generation

### Graph vs Queue
- graph = accepted knowledge
- expansion queue = potential additions requiring decision

### Mapping vs Retrieval
- mapping = intellectual structure of literature
- retrieval = acquisition of documents and data

## Design principles

- keep repo small and understandable
- single Python application
- deterministic, local-first operation
- explicit user control over ingestion
- avoid hidden automation that alters the graph

## Future direction

- richer citation integration
- improved PDF acquisition pipelines
- better SI detection and classification
- refined expansion ranking
