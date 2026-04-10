#!/usr/bin/env python3
"""Generate dependency graph visualization for PRDifferMCP.

This script analyzes Python imports and creates a visual dependency graph
showing relationships between modules and layers.
"""

import ast
import sys
from pathlib import Path
from collections import defaultdict


class DependencyAnalyzer:
    """Extract top-level import dependencies from a Python module.

    Only analyses module-scope and class-scope imports, not lazy imports
    inside function/method bodies (which are acceptable for fallback DI)."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.imports: set[str] = set()
        self.current_module = self._get_module_name(file_path)

    def _get_module_name(self, path: Path) -> str:
        """Convert file path to module name."""
        parts = path.parts
        try:
            # Find 'prdiffer' in path
            prdiffer_idx = parts.index("prdiffer")
            return ".".join(parts[prdiffer_idx:])
        except ValueError:
            # Not in prdiffer directory
            return ".".join(parts)

    def _collect_imports_from_node(self, node: ast.AST) -> None:
        """Collect import statements from a single AST node."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                self.imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            self.imports.add(node.module)

    def analyze(self, tree: ast.Module) -> None:
        """Analyze top-level and class-level imports only."""
        for node in ast.iter_child_nodes(tree):
            self._collect_imports_from_node(node)
            if isinstance(node, ast.ClassDef):
                for class_node in ast.iter_child_nodes(node):
                    self._collect_imports_from_node(class_node)


def analyze_directory(root: Path) -> dict[str, set[str]]:
    """Analyze all Python files in directory.

    Args:
        root: Root directory to analyze

    Returns:
        Dict mapping module name to its dependencies
    """
    dependencies = defaultdict(set)

    for py_file in root.rglob("*.py"):
        # Skip test files and __pycache__
        if "test" in py_file.parts or "__pycache__" in py_file.parts:
            continue

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)
            analyzer = DependencyAnalyzer(py_file)
            analyzer.analyze(tree)

            module = analyzer.current_module
            # Filter to only prdiffer dependencies
            prdiffer_deps = {imp for imp in analyzer.imports if "prdiffer" in imp}
            dependencies[module] = prdiffer_deps

        except Exception as e:
            print(f"Warning: Could not analyze {py_file}: {e}", file=sys.stderr)

    return dependencies


def detect_layer_violations(
    dependencies: dict[str, set[str]],
) -> list[tuple[str, str, str]]:
    """Detect Clean Architecture layer violations.

    Rules:
    - Domain should not depend on Application
    - Domain should not depend on Infrastructure
    - Application should not depend on Infrastructure

    Args:
        dependencies: Module dependency graph

    Returns:
        List of (module, dependency, violation_type) tuples
    """
    violations = []

    for module, deps in dependencies.items():
        for dep in deps:
            # Domain violations
            if module.startswith("prdiffer.domain"):
                if dep.startswith("prdiffer.application"):
                    violations.append((module, dep, "Domain -> Application"))
                elif dep.startswith("prdiffer.infrastructure"):
                    violations.append((module, dep, "Domain -> Infrastructure"))

            # Application violations
            elif module.startswith("prdiffer.application"):
                if dep.startswith("prdiffer.infrastructure"):
                    violations.append((module, dep, "Application -> Infrastructure"))

    return violations


def print_graph(dependencies: dict[str, set[str]]) -> None:
    """Print dependency graph as ASCII art.

    Args:
        dependencies: Module dependency graph
    """
    print("\n" + "=" * 80)
    print("DEPENDENCY GRAPH")
    print("=" * 80 + "\n")

    # Group by layer
    layers = {"Domain": [], "Application": [], "Infrastructure": []}

    for module in sorted(dependencies.keys()):
        if module.startswith("prdiffer.domain"):
            layers["Domain"].append(module)
        elif module.startswith("prdiffer.application"):
            layers["Application"].append(module)
        elif module.startswith("prdiffer.infrastructure"):
            layers["Infrastructure"].append(module)

    for layer_name, modules in layers.items():
        if modules:
            print(f"\n{layer_name.upper()} LAYER:")
            print("-" * 80)
            for module in sorted(modules):
                short_name = module.replace("prdiffer.", "")
                deps = sorted(dependencies[module])
                if deps:
                    short_deps = [d.replace("prdiffer.", "") for d in deps]
                    print(f"  {short_name}")
                    print(f"    → {', '.join(short_deps)}")
                else:
                    print(f"  {short_name} (no internal deps)")


def print_violations(violations: list[tuple[str, str, str]]) -> None:
    """Print detected violations.

    Args:
        violations: List of violations
    """
    print("\n" + "=" * 80)
    print("LAYER VIOLATIONS")
    print("=" * 80 + "\n")

    if not violations:
        print("✅ No layer violations detected!")
        return

    print(f"⚠️  Found {len(violations)} violation(s):\n")

    for i, (module, dep, violation_type) in enumerate(violations, 1):
        print(f"{i}. {violation_type}")
        print(f"   Module:     {module}")
        print(f"   Depends on:  {dep}")
        print()


def print_statistics(dependencies: dict[str, set[str]], violations: list[tuple[str, str, str]]) -> None:
    """Print architecture statistics.

    Args:
        dependencies: Module dependency graph
        violations: List of violations
    """
    print("\n" + "=" * 80)
    print("ARCHITECTURE STATISTICS")
    print("=" * 80 + "\n")

    total_modules = len(dependencies)
    total_edges = sum(len(deps) for deps in dependencies.values())

    # Count modules per layer
    layer_counts = defaultdict(int)
    for module in dependencies.keys():
        if module.startswith("prdiffer.domain"):
            layer_counts["Domain"] += 1
        elif module.startswith("prdiffer.application"):
            layer_counts["Application"] += 1
        elif module.startswith("prdiffer.infrastructure"):
            layer_counts["Infrastructure"] += 1

    print("Total Modules:          {}".format(total_modules))
    print("Total Dependencies:       {}".format(total_edges))
    print("Layer Violations:        {}".format(len(violations)))
    print("\nModules per Layer:")
    for layer, count in sorted(layer_counts.items()):
        print("  {:20} {:3}".format(layer, count))

    # Find most connected modules
    print("\nTop 5 Most Connected Modules:")
    sorted_by_deps = sorted(dependencies.items(), key=lambda x: len(x[1]), reverse=True)
    for module, deps in sorted_by_deps[:5]:
        short_name = module.replace("prdiffer.", "")
        print("  {:40} {:2} deps".format(short_name, len(deps)))


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate dependency graph for PRDifferMCP")
    parser.add_argument(
        "--path",
        type=str,
        default="prdiffer",
        help="Path to prdiffer directory (default: prdiffer)",
    )
    parser.add_argument("--output", type=str, help="Output file for DOT graph (requires graphviz)")

    args = parser.parse_args()

    # Find prdiffer directory
    root = Path(args.path)
    if not root.exists():
        print(f"Error: Directory {root} not found", file=sys.stderr)
        sys.exit(1)

    # Analyze dependencies
    print(f"Analyzing dependencies in {root}...")
    dependencies = analyze_directory(root)

    # Detect violations
    violations = detect_layer_violations(dependencies)

    # Print results
    print_graph(dependencies)
    print_violations(violations)
    print_statistics(dependencies, violations)

    # Exit with error code if violations found
    if violations:
        print(f"\n❌ Found {len(violations)} layer violation(s). Fix before proceeding.")
        sys.exit(1)
    else:
        print("\n✅ Architecture is clean!")
        sys.exit(0)


if __name__ == "__main__":
    main()
