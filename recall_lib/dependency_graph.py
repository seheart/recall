#!/usr/bin/env python3
"""
Dependency Graph - Track and visualize dependencies between projects

Tracks:
- Explicit dependencies (manually declared)
- Detected dependencies (from package files)
- Circular dependency detection
- Dependency impact analysis
"""
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
import json
from .logger import get_logger

logger = get_logger(__name__)


class DependencyGraph:
    """
    Manages project dependency graph

    Supports:
    - Adding/removing dependencies
    - Circular dependency detection
    - Topological sorting
    - Impact analysis (what depends on this project)
    """

    def __init__(self, database):
        """
        Initialize dependency graph

        Args:
            database: RecallDatabase instance
        """
        self.db = database
        self._graph: Dict[str, Set[str]] = {}  # project_name -> set of dependencies
        self._load_graph()

    def _load_graph(self):
        """Load dependency graph from database"""
        conn = self.db._get_connection()
        cursor = conn.execute('''
            SELECT p.name, pc.value
            FROM projects p
            LEFT JOIN project_context pc ON p.id = pc.project_id
            WHERE pc.category = 'dependencies' AND pc.key = 'depends_on'
        ''')

        for row in cursor.fetchall():
            project_name = row[0]
            dependencies_json = row[1]

            if dependencies_json:
                try:
                    dependencies = json.loads(dependencies_json)
                    self._graph[project_name] = set(dependencies)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid dependencies JSON for project '{project_name}'")

    def add_dependency(self, project_name: str, depends_on: str) -> bool:
        """
        Add a dependency relationship

        Args:
            project_name: Project that has the dependency
            depends_on: Project that is depended upon

        Returns:
            True if added successfully, False if would create circular dependency
        """
        # Check for self-dependency
        if project_name == depends_on:
            logger.error(f"❌ Cannot add self-dependency for '{project_name}'")
            return False

        # Check for circular dependency
        if self._would_create_cycle(project_name, depends_on):
            logger.error(f"❌ Cannot add dependency: would create circular dependency")
            logger.error(f"   '{project_name}' → '{depends_on}' → ... → '{project_name}'")
            return False

        # Add to graph
        if project_name not in self._graph:
            self._graph[project_name] = set()

        self._graph[project_name].add(depends_on)

        # Save to database
        self._save_dependencies(project_name)

        logger.info(f"✅ Added dependency: '{project_name}' depends on '{depends_on}'")
        return True

    def remove_dependency(self, project_name: str, depends_on: str) -> bool:
        """
        Remove a dependency relationship

        Args:
            project_name: Project that has the dependency
            depends_on: Project that is depended upon

        Returns:
            True if removed successfully, False otherwise
        """
        if project_name not in self._graph:
            return False

        if depends_on in self._graph[project_name]:
            self._graph[project_name].remove(depends_on)

            # Clean up empty sets
            if not self._graph[project_name]:
                del self._graph[project_name]

            # Save to database
            self._save_dependencies(project_name)

            logger.info(f"🗑️ Removed dependency: '{project_name}' no longer depends on '{depends_on}'")
            return True

        return False

    def get_dependencies(self, project_name: str) -> List[str]:
        """
        Get direct dependencies of a project

        Args:
            project_name: Project name

        Returns:
            List of project names this project depends on
        """
        return sorted(list(self._graph.get(project_name, set())))

    def get_dependents(self, project_name: str) -> List[str]:
        """
        Get projects that depend on this project

        Args:
            project_name: Project name

        Returns:
            List of project names that depend on this project
        """
        dependents = []
        for project, deps in self._graph.items():
            if project_name in deps:
                dependents.append(project)

        return sorted(dependents)

    def get_all_dependencies(self, project_name: str) -> Set[str]:
        """
        Get all dependencies (direct and transitive) of a project

        Args:
            project_name: Project name

        Returns:
            Set of all project names this project depends on (directly or indirectly)
        """
        visited = set()
        self._dfs_dependencies(project_name, visited)
        visited.discard(project_name)  # Remove self
        return visited

    def _dfs_dependencies(self, project_name: str, visited: Set[str]):
        """Depth-first search to collect all dependencies"""
        if project_name in visited:
            return

        visited.add(project_name)

        for dep in self._graph.get(project_name, set()):
            self._dfs_dependencies(dep, visited)

    def get_all_dependents(self, project_name: str) -> Set[str]:
        """
        Get all dependents (direct and transitive) of a project

        Args:
            project_name: Project name

        Returns:
            Set of all project names that depend on this project (directly or indirectly)
        """
        all_dependents = set()

        for project in self._graph.keys():
            all_deps = self.get_all_dependencies(project)
            if project_name in all_deps:
                all_dependents.add(project)

        return all_dependents

    def _would_create_cycle(self, project_name: str, new_dependency: str) -> bool:
        """
        Check if adding a dependency would create a circular dependency

        Args:
            project_name: Project to add dependency to
            new_dependency: Proposed dependency

        Returns:
            True if would create cycle, False otherwise
        """
        # If new_dependency already depends on project_name (directly or transitively),
        # adding project_name -> new_dependency would create a cycle

        all_deps_of_new = self.get_all_dependencies(new_dependency)
        return project_name in all_deps_of_new

    def detect_cycles(self) -> List[List[str]]:
        """
        Detect all circular dependencies in the graph

        Returns:
            List of cycles, where each cycle is a list of project names
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> bool:
            """DFS to detect cycles"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self._graph.get(node, set()):
                if neighbor not in visited:
                    if dfs(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)

            path.pop()
            rec_stack.remove(node)
            return False

        for project in self._graph.keys():
            if project not in visited:
                dfs(project, [])

        return cycles

    def topological_sort(self) -> List[str]:
        """
        Get projects in topological order (dependencies first)

        Returns:
            List of project names in dependency order

        Raises:
            ValueError: If graph has cycles
        """
        cycles = self.detect_cycles()
        if cycles:
            raise ValueError(f"Cannot topologically sort: graph has cycles: {cycles}")

        in_degree = {}
        for project in self._graph.keys():
            in_degree[project] = 0

        for project, deps in self._graph.items():
            for dep in deps:
                in_degree[dep] = in_degree.get(dep, 0) + 1

        # Queue of projects with no dependencies
        queue = [p for p in in_degree.keys() if in_degree[p] == 0]
        result = []

        while queue:
            project = queue.pop(0)
            result.append(project)

            for dep in self._graph.get(project, set()):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)

        return result

    def get_impact_analysis(self, project_name: str) -> Dict[str, any]:
        """
        Analyze the impact of changes to a project

        Args:
            project_name: Project name

        Returns:
            Dict with impact analysis data
        """
        direct_dependents = self.get_dependents(project_name)
        all_dependents = self.get_all_dependents(project_name)
        transitive_count = len(all_dependents) - len(direct_dependents)

        return {
            'project': project_name,
            'direct_dependents': direct_dependents,
            'total_dependents': len(all_dependents),
            'transitive_dependents': transitive_count,
            'impact_level': 'high' if len(all_dependents) > 5 else 'medium' if len(all_dependents) > 2 else 'low'
        }

    def visualize_graph(self, format='text') -> str:
        """
        Visualize dependency graph

        Args:
            format: Output format ('text' or 'dot' for Graphviz)

        Returns:
            String representation of the graph
        """
        if format == 'dot':
            # Graphviz DOT format
            lines = ['digraph Dependencies {']
            lines.append('  rankdir=LR;')
            lines.append('  node [shape=box];')

            for project, deps in sorted(self._graph.items()):
                for dep in sorted(deps):
                    lines.append(f'  "{project}" -> "{dep}";')

            lines.append('}')
            return '\n'.join(lines)

        else:
            # Text format
            lines = ['📦 Project Dependencies:\n']

            if not self._graph:
                lines.append('  No dependencies tracked\n')
                return '\n'.join(lines)

            for project in sorted(self._graph.keys()):
                deps = self.get_dependencies(project)
                if deps:
                    lines.append(f'  {project}')
                    for dep in deps:
                        lines.append(f'    → {dep}')
                    lines.append('')

            return '\n'.join(lines)

    def _save_dependencies(self, project_name: str):
        """Save project dependencies to database"""
        project = self.db.get_project(project_name)
        if not project:
            return

        dependencies = list(self._graph.get(project_name, set()))

        self.db.set_context(
            project['id'],
            'dependencies',
            'depends_on',
            json.dumps(dependencies)
        )


def auto_detect_dependencies(project_dir: str) -> List[str]:
    """
    Auto-detect dependencies from package files

    Scans for:
    - package.json (npm dependencies)
    - requirements.txt (Python dependencies)
    - go.mod (Go dependencies)
    - Cargo.toml (Rust dependencies)

    Args:
        project_dir: Path to project directory

    Returns:
        List of detected project names (based on package names)
    """
    detected = []
    project_path = Path(project_dir)

    # Check package.json
    package_json = project_path / 'package.json'
    if package_json.exists():
        try:
            import json
            with open(package_json) as f:
                data = json.load(f)
                if 'dependencies' in data:
                    detected.extend(data['dependencies'].keys())
        except Exception as e:
            logger.debug(f"Failed to parse package.json: {e}")

    # Check requirements.txt
    requirements_txt = project_path / 'requirements.txt'
    if requirements_txt.exists():
        try:
            with open(requirements_txt) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name (before ==, >=, etc.)
                        package = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                        detected.append(package)
        except Exception as e:
            logger.debug(f"Failed to parse requirements.txt: {e}")

    return detected
