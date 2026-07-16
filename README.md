# PyStructure

PyStructure is a Python static-analysis core for visualizing Python project structure and dependencies.

It scans Python source files, parses them with `ast`, and extracts:

- files and modules
- classes and functions
- import relationships
- graph nodes and edges for later visualization

## Goals

- Static analysis only, no code execution
- Standard library first, especially `ast`
- Small, well-separated responsibilities
- Easy to extend for a future PyCharm plugin UI

## Project Layout

- `src/pystructure/scanner.py`: file discovery and module naming
- `src/pystructure/analyzer.py`: AST parsing and symbol extraction
- `src/pystructure/import_resolver.py`: import normalization and module resolution helpers
- `src/pystructure/graph.py`: dependency graph assembly and serialization
- `src/pystructure/models.py`: shared dataclasses
- `src/pystructure/cli.py`: command-line entrypoint

## Run

```bash
python -m pystructure analyze path/to/project --json
```

## Tests

```bash
python -m unittest discover -s tests
```

## Notes

This repository currently contains only the analysis core scaffold. PyCharm integration can be layered on top of this engine later without changing the parser model.
