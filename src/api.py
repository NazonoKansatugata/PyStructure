from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analyzer import ProjectAnalyzer
from exporter import JsonExporter
from graph import DependencyGraph
from models import AnalysisResult


@dataclass(frozen=True)
class AnalysisBundle:
    analysis: AnalysisResult
    graph: DependencyGraph

    def to_dict(self) -> dict[str, Any]:
        return JsonExporter().payload(self.analysis, self.graph)


def analyze_project(root: Path) -> AnalysisBundle:
    analysis, graph = ProjectAnalyzer().build_graph(root)
    return AnalysisBundle(analysis=analysis, graph=graph)


def analyze_project_payload(root: Path) -> dict[str, Any]:
    return analyze_project(root).to_dict()