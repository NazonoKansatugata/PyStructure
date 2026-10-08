from __future__ import annotations

from collections import deque
from dataclasses import replace

from models import ModuleInfo
from symbol_resolver import SymbolResolver


class MetricsAnalyzer:
    """Compute module-level dependency metrics from internal imports.

    Entry points are modules with an ``if __name__ == "__main__"`` guard or named
    ``__main__``. When none exist, modules that nothing imports are used instead.
    """

    def apply(self, modules: list[ModuleInfo]) -> list[ModuleInfo]:
        names = {module.module_name for module in modules}
        resolver = SymbolResolver(modules)
        outgoing = {module.module_name: self._internal_dependencies(module, resolver) for module in modules}
        incoming: dict[str, set[str]] = {name: set() for name in names}
        for source, targets in outgoing.items():
            for target in targets:
                incoming[target].add(source)

        cyclic = self._cyclic_modules(outgoing)
        entries = self._entry_points(modules, incoming)
        depths = self._depths(outgoing, entries)

        return [
            replace(
                module,
                metrics=replace(
                    module.metrics,
                    fan_in=len(incoming[module.module_name]),
                    fan_out=len(outgoing[module.module_name]),
                    in_cycle=module.module_name in cyclic,
                    is_entry=module.module_name in entries,
                    depth=depths.get(module.module_name),
                ),
            )
            for module in modules
        ]

    def _internal_dependencies(self, module: ModuleInfo, resolver: SymbolResolver) -> set[str]:
        targets: set[str] = set()
        for import_info in module.imports:
            for _, internal in resolver.import_targets(import_info):
                targets.update(name for name in internal if name != module.module_name)
        return targets

    def _entry_points(self, modules: list[ModuleInfo], incoming: dict[str, set[str]]) -> set[str]:
        entries = {
            module.module_name
            for module in modules
            if module.has_main_guard or module.module_name.rsplit(".", 1)[-1] == "__main__"
        }
        if entries:
            return entries
        return {name for name, sources in incoming.items() if not sources}

    def _depths(self, outgoing: dict[str, set[str]], entries: set[str]) -> dict[str, int]:
        depths = {name: 0 for name in entries}
        queue = deque(sorted(entries))
        while queue:
            current = queue.popleft()
            for target in sorted(outgoing[current]):
                if target not in depths:
                    depths[target] = depths[current] + 1
                    queue.append(target)
        return depths

    def _cyclic_modules(self, outgoing: dict[str, set[str]]) -> set[str]:
        """Return modules that belong to a strongly connected component of size > 1 (iterative Tarjan)."""
        index_of: dict[str, int] = {}
        lowlink: dict[str, int] = {}
        on_stack: set[str] = set()
        stack: list[str] = []
        cyclic: set[str] = set()
        counter = 0

        for root in sorted(outgoing):
            if root in index_of:
                continue
            index_of[root] = lowlink[root] = counter
            counter += 1
            stack.append(root)
            on_stack.add(root)
            work = [(root, iter(sorted(outgoing[root])))]

            while work:
                node, children = work[-1]
                advanced = False
                for child in children:
                    if child not in index_of:
                        index_of[child] = lowlink[child] = counter
                        counter += 1
                        stack.append(child)
                        on_stack.add(child)
                        work.append((child, iter(sorted(outgoing[child]))))
                        advanced = True
                        break
                    if child in on_stack:
                        lowlink[node] = min(lowlink[node], index_of[child])
                if advanced:
                    continue

                work.pop()
                if work:
                    parent = work[-1][0]
                    lowlink[parent] = min(lowlink[parent], lowlink[node])
                if lowlink[node] == index_of[node]:
                    component: list[str] = []
                    while True:
                        member = stack.pop()
                        on_stack.discard(member)
                        component.append(member)
                        if member == node:
                            break
                    if len(component) > 1:
                        cyclic.update(component)

        return cyclic
