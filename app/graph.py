from __future__ import annotations

import math
from html import escape
from typing import Optional
from urllib.parse import quote

from app.models import Candidate, EdgeType, Graph, GraphEdge, GraphNode, NodeType, Project


def paper_node_id(candidate_id: str) -> str:
    return f"paper:{candidate_id}"


def author_node_id(author: str) -> str:
    return f"author:{author.lower()}"


def topic_node_id(topic: str) -> str:
    return f"topic:{topic.lower()}"


def update_graph_for_candidate(project: Project, candidate: Candidate) -> None:
    if candidate.decision != candidate.decision.YES:
        return

    node_ids = {node.node_id for node in project.graph.nodes}
    edge_ids = {edge.edge_id for edge in project.graph.edges}
    paper_id = paper_node_id(candidate.candidate_id)

    if paper_id not in node_ids:
        project.graph.nodes.append(
            GraphNode(node_id=paper_id, node_type=NodeType.PAPER, label=candidate.title)
        )
        node_ids.add(paper_id)

    for author in candidate.authors[:4]:
        aid = author_node_id(author)
        if aid not in node_ids:
            project.graph.nodes.append(
                GraphNode(node_id=aid, node_type=NodeType.AUTHOR, label=author)
            )
            node_ids.add(aid)
        eid = f"edge:{paper_id}:{aid}"
        if eid not in edge_ids:
            project.graph.edges.append(
                GraphEdge(
                    edge_id=eid,
                    edge_type=EdgeType.PAPER_AUTHOR,
                    source=paper_id,
                    target=aid,
                    label="author",
                )
            )
            edge_ids.add(eid)

    hints = [reason.replace("concept:", "") for reason in candidate.reasons if reason.startswith("concept:")]
    for topic in hints[:4]:
        tid = topic_node_id(topic)
        if tid not in node_ids:
            project.graph.nodes.append(
                GraphNode(node_id=tid, node_type=NodeType.TOPIC, label=topic.title())
            )
            node_ids.add(tid)
        eid = f"edge:{paper_id}:{tid}"
        if eid not in edge_ids:
            project.graph.edges.append(
                GraphEdge(
                    edge_id=eid,
                    edge_type=EdgeType.PAPER_TOPIC,
                    source=paper_id,
                    target=tid,
                    label="topic",
                )
            )
            edge_ids.add(eid)


def _candidate_id_from_node(node_id: str) -> Optional[str]:
    prefix = "paper:"
    if node_id.startswith(prefix):
        return node_id[len(prefix):]
    return None


def _workspace_href(project_id: Optional[str], node_id: str) -> Optional[str]:
    if not project_id:
        return None
    candidate_id = _candidate_id_from_node(node_id)
    if not candidate_id:
        return None
    return f"/projects/{quote(project_id)}/workspace?selected={quote(candidate_id)}"


def render_graph_svg(
    graph: Graph,
    selected_candidate_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> str:
    width, height = 980, 680
    cx, cy = width / 2, height / 2
    radius = 215
    nodes = graph.nodes
    positions: dict[str, tuple[float, float]] = {}
    total = max(len(nodes), 1)

    for index, node in enumerate(nodes):
        if node.node_type == NodeType.PAPER:
            r = radius * 0.42
        elif node.node_type == NodeType.AUTHOR:
            r = radius * 0.95
        else:
            r = radius * 1.28
        angle = (2 * math.pi * index) / total
        positions[node.node_id] = (cx + math.cos(angle) * r, cy + math.sin(angle) * r)

    pieces = [
        f'<svg viewBox="0 0 {width} {height}" class="graph-svg" xmlns="http://www.w3.org/2000/svg">',
        '<defs><filter id="glow"><feGaussianBlur stdDeviation="6" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
        '<rect width="100%" height="100%" rx="24" class="graph-bg"/>',
    ]

    for edge in graph.edges:
        if edge.source not in positions or edge.target not in positions:
            continue
        x1, y1 = positions[edge.source]
        x2, y2 = positions[edge.target]
        href = _workspace_href(project_id, edge.source) or _workspace_href(project_id, edge.target)
        line = (
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'class="graph-edge" data-source="{escape(edge.source)}" data-target="{escape(edge.target)}"/>'
        )
        if href:
            pieces.append(f'<a href="{escape(href)}" class="graph-link">{line}</a>')
        else:
            pieces.append(line)

    for node in nodes:
        x, y = positions[node.node_id]
        extra = " graph-node--selected" if selected_candidate_id and node.node_id.endswith(selected_candidate_id) else ""
        radius_px = 17 if node.node_type == NodeType.PAPER else 12
        circle = (
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius_px}" '
            f'class="graph-node graph-node--{escape(node.node_type.value)}{extra}" '
            f'filter="url(#glow)" data-node-id="{escape(node.node_id)}"/>'
            f'<text x="{x:.1f}" y="{y + 30:.1f}" text-anchor="middle" class="graph-label">{escape(node.label[:44])}</text>'
        )
        href = _workspace_href(project_id, node.node_id)
        if href:
            pieces.append(f'<a href="{escape(href)}" class="graph-link">{circle}</a>')
        else:
            pieces.append(circle)

    if not nodes:
        pieces.append('<text x="50%" y="50%" text-anchor="middle" class="graph-empty">Accept papers to grow your map.</text>')

    pieces.append('</svg>')
    return ''.join(pieces)
