#!/usr/bin/env python3
"""
Auto Analyzer - Automatically analyze project structure and populate recall context
"""
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from .project_memory import ProjectMemory
from .git_utils import get_recent_commits, get_status, get_branch_name, get_remote_url

from .logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class ProjectAnalyzer:
    """Analyzes a project directory and extracts comprehensive context"""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.context = {}

    def analyze(self, show_progress: bool = True) -> Dict:
        """Run all analysis methods and return comprehensive context"""
        from rich.progress import Progress, SpinnerColumn, TextColumn

        analysis_steps = [
            ("Analyzing git repository...", self.analyze_git),
            ("Tracking hot files...", self.analyze_hot_files),
            ("Detecting entry points...", self.analyze_entry_points),
            ("Checking package.json...", self.analyze_package_json),
            ("Scanning Python files...", self.analyze_python),
            ("Detecting Docker setup...", self.analyze_docker),
            ("Checking database config...", self.analyze_database),
            ("Analyzing directory structure...", self.analyze_structure),
            ("Reading README...", self.analyze_readme),
            ("Detecting testing setup...", self.analyze_testing),
            ("Checking deployment config...", self.analyze_deployment),
            ("Analyzing environment files...", self.analyze_environment),
            ("Detecting external integrations...", self.analyze_external_integrations),
            ("Analyzing working tree state...", self.analyze_working_tree),
            ("Extracting workflows...", self.analyze_workflows),
            ("Tracking known issues...", self.analyze_known_issues),
            ("Detecting architecture patterns...", self.analyze_architecture_patterns),
            ("Analyzing file relationships...", self.analyze_file_relationships),
            ("Checking project health...", self.analyze_health_metrics),
            ("Counting TODOs/FIXMEs...", self.analyze_todos),
        ]

        if show_progress:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Analyzing project...", total=len(analysis_steps))

                for description, analysis_func in analysis_steps:
                    progress.update(task, description=description)
                    analysis_func()
                    progress.advance(task)
        else:
            # Run without progress bar
            for _, analysis_func in analysis_steps:
                analysis_func()

        return self.context

    def analyze_git(self):
        """Extract git information using git_utils"""
        project_dir_str = str(self.project_dir)

        # Get recent commits
        commits = get_recent_commits(project_dir_str, limit=5)
        if commits:
            self.context['git_recent_commits'] = f"{commits[0]['hash']}: {commits[0]['message']}"

        # Get repo status
        status = get_status(project_dir_str)
        if status['has_changes']:
            total_changes = len(status['staged_files']) + len(status['unstaged_files']) + len(status['untracked_files'])
            self.context['git_status'] = f"{total_changes} uncommitted changes"
        else:
            self.context['git_status'] = "Clean"

        # Get branch name
        branch = get_branch_name(project_dir_str)
        if branch:
            self.context['git_branch'] = branch

        # Get remote URL
        remote = get_remote_url(project_dir_str)
        if remote:
            self.context['git_remote'] = remote

    def analyze_package_json(self):
        """Extract package.json details for Node/JS projects"""
        package_file = self.project_dir / 'package.json'
        if not package_file.exists():
            # Try subdirectories
            for subdir in self.project_dir.iterdir():
                if subdir.is_dir():
                    sub_package = subdir / 'package.json'
                    if sub_package.exists():
                        package_file = sub_package
                        break

        if not package_file.exists():
            return

        try:
            with open(package_file, 'r') as f:
                data = json.load(f)

            self.context['package_name'] = data.get('name')

            if 'scripts' in data:
                self.context['npm_scripts'] = ', '.join(data['scripts'].keys())

            # Detect framework from dependencies
            deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}

            frameworks = []
            if 'react' in deps:
                frameworks.append(f"React {deps['react']}")
            if 'vue' in deps:
                frameworks.append(f"Vue {deps['vue']}")
            if 'next' in deps:
                frameworks.append(f"Next.js {deps['next']}")
            if 'vite' in deps:
                frameworks.append(f"Vite {deps['vite']}")
            if 'tailwindcss' in deps:
                frameworks.append(f"TailwindCSS {deps['tailwindcss']}")
            if 'gsap' in deps:
                frameworks.append(f"GSAP {deps['gsap']}")

            if frameworks:
                self.context['tech_stack'] = ' + '.join(frameworks)

        except Exception as e:
            logger.info(f"package.json analysis failed: {e}")

    def analyze_structure(self):
        """Analyze directory structure"""
        key_dirs = []
        key_files = []

        # Look for common directories
        common_dirs = ['src', 'dist', 'build', 'public', 'docs', 'tests', 'components', 'pages']
        for dirname in common_dirs:
            if (self.project_dir / dirname).exists():
                key_dirs.append(dirname)

        # Look for config files
        config_files = [
            'package.json', 'vite.config.js', 'tailwind.config.js',
            'tsconfig.json', '.env', 'README.md', 'docker-compose.yml',
            'Dockerfile', 'requirements.txt', 'setup.py', 'Makefile'
        ]
        for filename in config_files:
            if (self.project_dir / filename).exists():
                key_files.append(filename)

        if key_dirs:
            self.context['key_directories'] = ', '.join(key_dirs)
        if key_files:
            self.context['config_files'] = ', '.join(key_files)

    def analyze_readme(self):
        """Extract key info from README"""
        readme_file = self.project_dir / 'README.md'
        if not readme_file.exists():
            return

        try:
            with open(readme_file, 'r') as f:
                content = f.read()

            # Extract first paragraph as description
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            if len(lines) > 1:
                # Skip title, get first real paragraph
                for i, line in enumerate(lines):
                    if not line.startswith('#') and len(line) > 20:
                        self.context['readme_description'] = line[:200]
                        break

        except Exception as e:
            logger.info(f"README analysis failed: {e}")

    def analyze_python(self):
        """Analyze Python project files"""
        # Check for requirements.txt
        req_file = self.project_dir / 'requirements.txt'
        if req_file.exists():
            try:
                with open(req_file, 'r') as f:
                    lines = [l.strip() for l in f.readlines() if l.strip() and not l.startswith('#')]
                    self.context['python_dependencies'] = f"{len(lines)} packages in requirements.txt"
                    # Extract major frameworks
                    frameworks = []
                    for line in lines:
                        lower = line.lower()
                        if 'django' in lower:
                            frameworks.append('Django')
                        elif 'flask' in lower:
                            frameworks.append('Flask')
                        elif 'fastapi' in lower:
                            frameworks.append('FastAPI')
                        elif 'pytest' in lower:
                            frameworks.append('pytest')
                    if frameworks:
                        self.context['python_frameworks'] = ', '.join(set(frameworks))
            except Exception as e:
                logger.info(f"requirements.txt analysis failed: {e}")

        # Check for setup.py or pyproject.toml
        if (self.project_dir / 'setup.py').exists():
            self.context['python_package'] = 'setup.py found (installable package)'
        if (self.project_dir / 'pyproject.toml').exists():
            self.context['python_package'] = 'pyproject.toml found (modern Python package)'

        # Check for virtual environment
        venv_dirs = ['.venv', 'venv', 'env']
        for vdir in venv_dirs:
            if (self.project_dir / vdir).exists():
                self.context['python_venv'] = f"{vdir}/ directory found"
                break

    def analyze_docker(self):
        """Analyze Docker configuration"""
        if (self.project_dir / 'Dockerfile').exists():
            self.context['docker'] = 'Dockerfile found'

        if (self.project_dir / 'docker-compose.yml').exists():
            try:
                with open(self.project_dir / 'docker-compose.yml', 'r') as f:
                    content = f.read()
                    # Count services
                    service_count = content.count('image:') + content.count('build:')
                    self.context['docker_compose'] = f"docker-compose.yml with ~{service_count} services"
            except Exception as e:
                self.context['docker_compose'] = 'docker-compose.yml found'

        if (self.project_dir / '.dockerignore').exists():
            self.context['docker_ignore'] = '.dockerignore configured'

    def analyze_database(self):
        """Detect database usage and migrations"""
        db_indicators = []

        # Check for migration directories
        migration_dirs = [
            'migrations', 'alembic', 'db/migrations',
            'prisma/migrations', 'drizzle'
        ]
        for mdir in migration_dirs:
            if (self.project_dir / mdir).exists():
                db_indicators.append(f"{mdir}/ migrations found")

        # Check for schema files
        schema_files = [
            'schema.prisma', 'schema.sql', 'schema.rb',
            'models.py', 'db/schema.rb'
        ]
        for sfile in schema_files:
            if (self.project_dir / sfile).exists():
                db_indicators.append(f"{sfile} schema")

        if db_indicators:
            self.context['database'] = ', '.join(db_indicators)

    def analyze_testing(self):
        """Analyze testing setup"""
        test_indicators = []

        # Check for test directories
        test_dirs = ['tests', 'test', '__tests__', 'spec']
        for tdir in test_dirs:
            if (self.project_dir / tdir).exists():
                # Count test files
                try:
                    test_files = list(Path(self.project_dir / tdir).rglob('test_*.py'))
                    test_files += list(Path(self.project_dir / tdir).rglob('*_test.py'))
                    test_files += list(Path(self.project_dir / tdir).rglob('*.test.js'))
                    test_files += list(Path(self.project_dir / tdir).rglob('*.spec.js'))
                    if test_files:
                        test_indicators.append(f"{tdir}/ with {len(test_files)} test files")
                    else:
                        test_indicators.append(f"{tdir}/ directory")
                except (OSError, PermissionError, ValueError) as e:
                    logger.debug(f"Could not scan test directory {tdir}: {e}")
                    test_indicators.append(f"{tdir}/ directory")

        # Check for test config files
        test_configs = [
            'pytest.ini', 'jest.config.js', 'vitest.config.js',
            '.coveragerc', 'coverage.json'
        ]
        for tconfig in test_configs:
            if (self.project_dir / tconfig).exists():
                test_indicators.append(f"{tconfig}")

        if test_indicators:
            self.context['testing'] = ', '.join(test_indicators)

    def analyze_deployment(self):
        """Analyze deployment configuration"""
        deploy_indicators = []

        # CI/CD files
        ci_files = [
            '.github/workflows', '.gitlab-ci.yml', '.circleci/config.yml',
            'Jenkinsfile', '.travis.yml', 'azure-pipelines.yml'
        ]
        for cifile in ci_files:
            if (self.project_dir / cifile).exists():
                deploy_indicators.append(cifile)

        # Platform configs
        platform_files = [
            'vercel.json', 'netlify.toml', 'render.yaml',
            'railway.json', 'fly.toml', 'app.yaml'
        ]
        for pfile in platform_files:
            if (self.project_dir / pfile).exists():
                deploy_indicators.append(pfile)

        # Server configs
        server_files = ['nginx.conf', 'apache.conf', 'Caddyfile']
        for sfile in server_files:
            if (self.project_dir / sfile).exists():
                deploy_indicators.append(sfile)

        if deploy_indicators:
            self.context['deployment'] = ', '.join(deploy_indicators)

    def _is_sensitive_env_var(self, key: str) -> bool:
        """
        Check if environment variable name suggests sensitive data

        Args:
            key: Environment variable name

        Returns:
            True if key appears to contain sensitive data
        """
        import re
        sensitive_patterns = [
            r'password', r'passwd', r'pwd',
            r'secret', r'api[_-]?key', r'token',
            r'private[_-]?key', r'access[_-]?key',
            r'credential', r'auth', r'bearer',
            r'session[_-]?key', r'jwt',
            r'oauth', r'passphrase'
        ]
        key_lower = key.lower()
        return any(re.search(pattern, key_lower) for pattern in sensitive_patterns)

    def analyze_environment(self):
        """Analyze environment configuration (excludes sensitive vars)"""
        env_indicators = []

        # Environment files
        env_files = ['.env', '.env.example', '.env.local', '.env.production']
        for efile in env_files:
            if (self.project_dir / efile).exists():
                try:
                    with open(self.project_dir / efile, 'r') as f:
                        non_sensitive_count = 0
                        sensitive_count = 0
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                # Parse KEY=value format
                                if '=' in line:
                                    key = line.split('=')[0].strip()
                                    if self._is_sensitive_env_var(key):
                                        sensitive_count += 1
                                    else:
                                        non_sensitive_count += 1
                                else:
                                    non_sensitive_count += 1

                        # Report counts, indicating sensitive vars were filtered
                        if sensitive_count > 0:
                            env_indicators.append(
                                f"{efile} ({non_sensitive_count} vars, {sensitive_count} sensitive)"
                            )
                        else:
                            env_indicators.append(f"{efile} ({non_sensitive_count} vars)")
                except (IOError, UnicodeDecodeError, PermissionError) as e:
                    logger.debug(f"Could not read env file {efile}: {e}")
                    env_indicators.append(efile)

        # Config directories
        if (self.project_dir / 'config').exists():
            env_indicators.append('config/ directory')

        if env_indicators:
            self.context['environment_config'] = ', '.join(env_indicators)

    def analyze_todos(self):
        """Extract TODO/FIXME comments from code"""
        todo_count = 0
        fixme_count = 0

        # Search common code file extensions
        extensions = ['.js', '.jsx', '.ts', '.tsx', '.py', '.go', '.rb', '.java']

        try:
            for ext in extensions:
                for filepath in self.project_dir.rglob(f'*{ext}'):
                    # Skip node_modules and similar
                    if 'node_modules' in str(filepath) or '.venv' in str(filepath):
                        continue
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            todo_count += content.count('TODO')
                            fixme_count += content.count('FIXME')
                    except (IOError, UnicodeDecodeError, PermissionError):
                        continue

            if todo_count > 0 or fixme_count > 0:
                self.context['code_todos'] = f"{todo_count} TODOs, {fixme_count} FIXMEs in codebase"
        except Exception as e:
            pass  # Silent fail for TODO analysis

    def analyze_hot_files(self):
        """Track most frequently modified files in last 7 days"""
        try:
            result = subprocess.run(
                ['git', 'log', '--pretty=format:', '--name-only', '--since=7.days'],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                files = [f for f in result.stdout.split('\n') if f.strip()]
                from collections import Counter
                file_counts = Counter(files)
                hot_files = file_counts.most_common(5)
                if hot_files:
                    hot_list = [f"{file} ({count} changes)" for file, count in hot_files]
                    self.context['hot_files'] = ', '.join(hot_list)
        except Exception as e:
            pass

    def analyze_entry_points(self):
        """Detect main entry points and key files"""
        entry_points = []

        # Check for common entry points
        entry_files = [
            ('main.py', 'Python main'),
            ('app.py', 'Flask/FastAPI app'),
            ('server.js', 'Node server'),
            ('index.js', 'JavaScript entry'),
            ('src/main.js', 'Vue/React entry'),
            ('src/index.js', 'React entry'),
            ('src/App.svelte', 'Svelte app'),
            ('src/App.jsx', 'React app'),
            ('bin/', 'CLI scripts'),
            ('cmd/', 'Go commands'),
            ('main.go', 'Go main'),
        ]

        for file_path, description in entry_files:
            full_path = self.project_dir / file_path
            if full_path.exists():
                entry_points.append(f"{file_path} ({description})")

        if entry_points:
            self.context['entry_points'] = ', '.join(entry_points)

    def analyze_external_integrations(self):
        """Detect external APIs and services"""
        integrations = set()

        # Search code for common API patterns
        patterns = {
            'api.github.com': 'GitHub API',
            'api.openai.com': 'OpenAI API',
            'stripe.com': 'Stripe',
            'twilio.com': 'Twilio',
            'sendgrid': 'SendGrid',
            'amazonaws.com': 'AWS',
            'googleapis.com': 'Google APIs',
            'api.anthropic.com': 'Anthropic API',
        }

        try:
            # Search common file types
            for ext in ['.py', '.js', '.ts', '.go', '.rb', '.env.example']:
                for filepath in self.project_dir.rglob(f'*{ext}'):
                    if 'node_modules' in str(filepath) or '.venv' in str(filepath):
                        continue
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            for pattern, name in patterns.items():
                                if pattern in content:
                                    integrations.add(name)
                    except (IOError, PermissionError):
                        continue
        except Exception:
            pass

        # Check docker-compose for services
        docker_compose = self.project_dir / 'docker-compose.yml'
        if docker_compose.exists():
            try:
                with open(docker_compose, 'r') as f:
                    content = f.read().lower()
                    if 'postgres' in content:
                        integrations.add('PostgreSQL')
                    if 'redis' in content:
                        integrations.add('Redis')
                    if 'mongodb' in content:
                        integrations.add('MongoDB')
                    if 'mysql' in content:
                        integrations.add('MySQL')
            except Exception:
                pass

        if integrations:
            self.context['external_integrations'] = ', '.join(sorted(integrations))

    def analyze_working_tree(self):
        """Capture current uncommitted changes"""
        try:
            from .git_utils import get_status
            status = get_status(str(self.project_dir))

            if status['has_changes']:
                modified = status['staged_files'] + status['unstaged_files']
                if modified:
                    # Limit to top 5 files
                    files = modified[:5]
                    self.context['working_tree_modified'] = ', '.join(files)

                if status['staged_files']:
                    self.context['working_tree_staged'] = f"{len(status['staged_files'])} files staged"

                # Get current branch
                result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    cwd=str(self.project_dir),
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    branch = result.stdout.strip()
                    self.context['working_tree_branch'] = branch
        except Exception:
            pass

    def analyze_workflows(self):
        """Extract common workflows from package.json, Makefile, README"""
        workflows = {}

        # Check package.json scripts
        package_json = self.project_dir / 'package.json'
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    scripts = data.get('scripts', {})
                    for name in ['dev', 'start', 'test', 'build', 'lint', 'deploy']:
                        if name in scripts:
                            workflows[name] = f"npm run {name}"
            except Exception:
                pass

        # Check Makefile
        makefile = self.project_dir / 'Makefile'
        if makefile.exists():
            try:
                with open(makefile, 'r') as f:
                    for line in f:
                        if ':' in line and not line.startswith('\t') and not line.startswith('#'):
                            target = line.split(':')[0].strip()
                            if target in ['test', 'build', 'deploy', 'install', 'clean', 'run']:
                                workflows[target] = f"make {target}"
            except Exception:
                pass

        # Check for Python
        if (self.project_dir / 'setup.py').exists() or (self.project_dir / 'pyproject.toml').exists():
            if (self.project_dir / 'tests').exists():
                workflows['test'] = 'pytest'

        # Check for shell scripts
        for script in ['run.sh', 'start.sh', 'test.sh', 'build.sh', 'deploy.sh']:
            if (self.project_dir / script).exists():
                name = script.replace('.sh', '')
                workflows[name] = f'./{script}'

        if workflows:
            workflow_list = [f"{k}: {v}" for k, v in workflows.items()]
            self.context['workflows'] = ' | '.join(workflow_list)

    def analyze_known_issues(self):
        """Track known issues from TODOs, FIXMEs, and comments"""
        issues = []

        extensions = ['.js', '.jsx', '.ts', '.tsx', '.py', '.go', '.rb', '.java', '.svelte', '.vue']

        try:
            for ext in extensions:
                for filepath in self.project_dir.rglob(f'*{ext}'):
                    if 'node_modules' in str(filepath) or '.venv' in str(filepath):
                        continue
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            for i, line in enumerate(lines, 1):
                                line_upper = line.upper()
                                if 'FIXME' in line_upper or 'BUG' in line_upper or 'XXX' in line_upper:
                                    # Extract the comment
                                    comment = line.strip()
                                    if len(comment) > 80:
                                        comment = comment[:77] + '...'
                                    rel_path = filepath.relative_to(self.project_dir)
                                    issues.append(f"{rel_path}:{i} - {comment}")
                                    if len(issues) >= 5:  # Limit to top 5
                                        break
                            if len(issues) >= 5:
                                break
                    except (IOError, UnicodeDecodeError, PermissionError):
                        continue
                if len(issues) >= 5:
                    break
        except Exception:
            pass

        if issues:
            self.context['known_issues'] = ' | '.join(issues)

    def analyze_architecture_patterns(self):
        """Detect architectural patterns and style"""
        patterns = []

        # Check for common architecture patterns
        if (self.project_dir / 'backend').exists() and (self.project_dir / 'frontend').exists():
            patterns.append('Client-Server separation')

        if (self.project_dir / 'api').exists() or any(f.name in ['routes.py', 'routes.js', 'api.py', 'api.js'] for f in self.project_dir.glob('**/*') if f.is_file()):
            patterns.append('REST API')

        # Check for specific frameworks
        if (self.project_dir / 'components').exists():
            patterns.append('Component-based UI')

        # Check for database
        if any((self.project_dir / f).exists() for f in ['models.py', 'schema.sql', 'schema.prisma']):
            patterns.append('Database-backed')

        # Check for microservices
        docker_compose = self.project_dir / 'docker-compose.yml'
        if docker_compose.exists():
            try:
                with open(docker_compose, 'r') as f:
                    content = f.read()
                    if content.count('image:') + content.count('build:') > 2:
                        patterns.append('Microservices (Docker)')
            except Exception:
                pass

        # Check for real-time features
        try:
            for filepath in self.project_dir.rglob('*.js'):
                if 'node_modules' in str(filepath):
                    continue
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if 'socket.io' in content or 'WebSocket' in content:
                        patterns.append('Real-time (WebSocket)')
                        break
        except Exception:
            pass

        if patterns:
            self.context['architecture_patterns'] = ', '.join(patterns)

    def analyze_file_relationships(self):
        """Analyze which files commonly change together"""
        try:
            # Get commits from last 30 days with file lists
            result = subprocess.run(
                ['git', 'log', '--pretty=format:%H', '--name-only', '--since=30.days'],
                cwd=str(self.project_dir),
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return

            # Parse commits
            lines = result.stdout.split('\n')
            commits = []
            current_commit = []

            for line in lines:
                if not line.strip():
                    if current_commit:
                        commits.append(current_commit)
                        current_commit = []
                elif len(line) == 40:  # Git hash
                    if current_commit:
                        commits.append(current_commit)
                    current_commit = []
                else:
                    current_commit.append(line.strip())

            if current_commit:
                commits.append(current_commit)

            # Find file pairs that change together
            from collections import Counter
            pairs = Counter()

            for commit_files in commits:
                if len(commit_files) > 1:
                    # Create pairs
                    for i, file1 in enumerate(commit_files):
                        for file2 in commit_files[i+1:]:
                            pair = tuple(sorted([file1, file2]))
                            pairs[pair] += 1

            # Get top coupled files
            top_pairs = pairs.most_common(3)
            if top_pairs and top_pairs[0][1] > 2:  # Only if changed together 3+ times
                coupled = []
                for (file1, file2), count in top_pairs:
                    if count > 2:
                        coupled.append(f"[{file1} ↔ {file2}] ({count} times)")

                if coupled:
                    self.context['file_relationships'] = ' | '.join(coupled)
        except Exception:
            pass

    def analyze_health_metrics(self):
        """Analyze project health metrics"""
        metrics = []

        # Check if tests exist and try to get status
        test_dirs = ['tests', 'test', '__tests__']
        has_tests = any((self.project_dir / d).exists() for d in test_dirs)

        if has_tests:
            # Try to find test results
            test_result_files = [
                '.pytest_cache/v/cache/lastfailed',
                'coverage.json',
                '.coverage'
            ]

            for result_file in test_result_files:
                if (self.project_dir / result_file).exists():
                    metrics.append('Tests available')
                    break

        # Check for CI/CD
        ci_files = ['.github/workflows', '.gitlab-ci.yml', '.circleci', 'Jenkinsfile']
        for ci_file in ci_files:
            if (self.project_dir / ci_file).exists():
                metrics.append('CI/CD configured')
                break

        # Check build time from package.json or similar
        package_json = self.project_dir / 'package.json'
        if package_json.exists():
            metrics.append('Node.js build system')

        # Check for linting
        lint_files = ['.eslintrc', '.pylintrc', 'pyproject.toml', '.flake8']
        for lint_file in lint_files:
            if (self.project_dir / lint_file).exists():
                metrics.append('Linting configured')
                break

        if metrics:
            self.context['health_metrics'] = ', '.join(metrics)


def auto_populate_recall(project_name: str, project_dir: str = None) -> bool:
    """Automatically analyze project and populate recall with comprehensive context"""
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

    if project_dir is None:
        project_dir = os.getcwd()

    logger.info(f"🔍 Analyzing project: {project_name}")
    logger.info(f"📁 Directory: {project_dir}\n")

    analyzer = ProjectAnalyzer(project_dir)
    context = analyzer.analyze(show_progress=True)

    memory = ProjectMemory()

    # Check if project exists
    if not memory.project_exists(project_name):
        from .fuzzy_match import suggest_project
        logger.error(f"❌ Project '{project_name}' not found in recall")
        suggestion = suggest_project(project_name, memory)
        if suggestion:
            logger.info(suggestion)
        else:
            logger.info(f"💡 Create it first with: recall {project_name} --create")
        return False

    project = memory.db.get_project(project_name)
    project_id = project['id']

    # Update with analyzed context
    logger.info("\n📝 Populating context:")

    for key, value in context.items():
        category = 'auto_analyzed'
        if key.startswith('git_'):
            category = 'git'
        elif key.startswith('npm_') or key == 'package_name':
            category = 'npm'
        elif key == 'tech_stack' or key == 'architecture_patterns':
            category = 'architecture'
        elif 'dir' in key or 'file' in key or key == 'hot_files' or key == 'entry_points' or key == 'file_relationships':
            category = 'structure'
        elif 'readme' in key:
            category = 'info'
        elif key.startswith('working_tree_'):
            category = 'working_tree'
        elif key == 'workflows':
            category = 'workflows'
        elif key == 'external_integrations':
            category = 'integrations'
        elif key == 'known_issues':
            category = 'issues'
        elif key == 'health_metrics':
            category = 'health'

        memory.db.set_context(project_id, category, key, str(value))
        logger.info(f"  • {category}/{key}: {value[:80]}{'...' if len(str(value)) > 80 else ''}")

    # Auto-populate description from README if missing
    if not project.get('description') and 'readme_description' in context:
        readme_desc = context['readme_description']
        # Clean up and limit to reasonable length
        if len(readme_desc) > 200:
            readme_desc = readme_desc[:197] + '...'
        with memory.db.get_connection() as conn:
            conn.execute(
                'UPDATE projects SET description = ? WHERE id = ?',
                (readme_desc, project_id)
            )
            conn.commit()
        logger.info(f"  ✨ Auto-set description from README")

    # Auto-add tags based on detected technology
    tags_to_add = set()

    # Detect bash/shell scripts
    has_shell_script = False
    for file in Path(project_dir).iterdir():
        if file.is_file() and file.suffix in ['.sh', ''] and os.access(file, os.X_OK):
            try:
                with open(file, 'r') as f:
                    first_line = f.readline()
                    if first_line.startswith('#!') and ('bash' in first_line or 'sh' in first_line):
                        has_shell_script = True
                        break
            except:
                pass

    if has_shell_script:
        tags_to_add.add('bash')
        tags_to_add.add('tool')
        # Check if script name suggests automation
        for file in Path(project_dir).iterdir():
            if file.is_file() and file.suffix in ['.sh', ''] and os.access(file, os.X_OK):
                fname_lower = file.name.lower()
                if any(keyword in fname_lower for keyword in ['auto', 'deploy', 'build', 'setup', 'install', 'wrap', 'run']):
                    tags_to_add.add('automation')
                    break

    # Detect web projects
    if 'package_name' in context or 'npm_scripts' in context:
        tags_to_add.add('web')

    # Detect frameworks
    if 'tech_stack' in context:
        tech = context['tech_stack'].lower()
        if 'react' in tech:
            tags_to_add.add('react')
        if 'vue' in tech:
            tags_to_add.add('vue')
        if 'svelte' in tech:
            tags_to_add.add('svelte')
        if 'next' in tech:
            tags_to_add.add('nextjs')
        if 'tailwind' in tech:
            tags_to_add.add('tailwind')

    # Detect Python projects
    if 'python_dependencies' in context or 'python_package' in context:
        tags_to_add.add('python')

    if 'python_frameworks' in context:
        frameworks = context['python_frameworks'].lower()
        if 'django' in frameworks:
            tags_to_add.add('django')
        if 'flask' in frameworks:
            tags_to_add.add('flask')
        if 'fastapi' in frameworks:
            tags_to_add.add('fastapi')

    # Detect CLI tools
    if 'python_package' in context and 'setup.py' in context.get('config_files', ''):
        tags_to_add.add('cli')
        tags_to_add.add('tool')

    # Detect Docker projects
    if 'docker' in context or 'docker_compose' in context:
        tags_to_add.add('docker')

    # Detect testing
    if 'testing' in context:
        tags_to_add.add('tested')

    # Detect monitoring/observability from project name or description
    project_name_lower = project_name.lower()
    if 'monitor' in project_name_lower or 'observ' in project_name_lower:
        tags_to_add.add('monitoring')

    # Detect portfolio/personal sites
    readme_desc = context.get('readme_description', '').lower()
    if 'portfolio' in readme_desc or 'personal' in readme_desc:
        tags_to_add.add('portfolio')

    # Detect consulting/business sites
    if 'consulting' in readme_desc or 'business' in readme_desc or 'professional' in readme_desc:
        tags_to_add.add('consulting')

    # Get existing tags to avoid duplicates
    existing_tags = set(memory.get_tags(project_name))
    new_tags = tags_to_add - existing_tags

    # Add new tags
    if new_tags:
        logger.info(f"\n🏷️  Auto-adding tags:")
        for tag in sorted(new_tags):
            memory.add_tag(project_name, tag)
            logger.info(f"  • {tag}")

    logger.info(f"\n✅ Auto-populated {len(context)} context items for '{project_name}'")
    if new_tags:
        logger.info(f"✅ Auto-added {len(new_tags)} tag(s)")
    logger.info(f"💡 View with: recall {project_name}")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        logger.info("Usage: auto_analyzer.py <project-name> [project-dir]")
        sys.exit(1)

    project_name = sys.argv[1]
    project_dir = sys.argv[2] if len(sys.argv) > 2 else None

    success = auto_populate_recall(project_name, project_dir)
    sys.exit(0 if success else 1)
