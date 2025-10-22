#!/usr/bin/env python3
"""
GitHub Plugin - Integrate Recall with GitHub repositories

Features:
- Sync issues to project context
- Create GitHub issues from sessions
- Fetch repository metadata
- Link commits to issues
- Track pull requests
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
import requests
from datetime import datetime

# Add parent directory to path to import recall_lib
sys.path.insert(0, str(Path(__file__).parent.parent))

from recall_lib.plugin_base import RecallPlugin, PluginContext, PluginHookPoints
from recall_lib.logger import get_logger

logger = get_logger(__name__)


class GitHubPlugin(RecallPlugin):
    """
    GitHub integration plugin for Recall

    Syncs GitHub issues, PRs, and repository metadata with project context
    """

    API_BASE = "https://api.github.com"

    @property
    def name(self) -> str:
        return "github"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Sync GitHub issues, PRs, and repository metadata with project context"

    @property
    def author(self) -> str:
        return "Recall Team"

    def initialize(self) -> bool:
        """Initialize the GitHub plugin"""
        logger.info(f"🔌 Initializing {self.name} plugin")

        # Validate configuration
        self.token = self.config.get("token")
        if not self.token:
            logger.warning("⚠️ GitHub token not configured - API rate limits will apply")

        self.auto_sync = self.config.get("auto_sync", True)
        self.sync_issues = self.config.get("sync_issues", True)
        self.sync_prs = self.config.get("sync_prs", True)
        self.create_issues_from_sessions = self.config.get("create_issues_from_sessions", False)

        return True

    def get_config_schema(self):
        """Define configuration schema"""
        return {
            "token": {
                "type": "string",
                "required": False,
                "description": "GitHub personal access token (for higher rate limits and private repos)",
            },
            "auto_sync": {
                "type": "bool",
                "default": True,
                "description": "Automatically sync GitHub data when analyzing projects",
            },
            "sync_issues": {
                "type": "bool",
                "default": True,
                "description": "Sync GitHub issues to context",
            },
            "sync_prs": {
                "type": "bool",
                "default": True,
                "description": "Sync GitHub pull requests to context",
            },
            "create_issues_from_sessions": {
                "type": "bool",
                "default": False,
                "description": "Create GitHub issues from session accomplishments (requires token)",
            },
            "repo_owner": {
                "type": "string",
                "required": False,
                "description": "Default repository owner (can be overridden per project)",
            },
            "repo_name": {
                "type": "string",
                "required": False,
                "description": "Default repository name (can be overridden per project)",
            },
        }

    def register_hooks(self):
        """Register hook handlers"""
        return {
            PluginHookPoints.PROJECT_POST_ANALYZE: self.on_project_analyzed,
            PluginHookPoints.SESSION_POST_CREATE: self.on_session_created,
        }

    def get_commands(self):
        """Register custom commands"""
        return {
            "sync": self.sync_github,
            "issues": self.list_issues,
            "prs": self.list_prs,
            "repo-info": self.show_repo_info,
            "create-issue": self.create_issue,
        }

    # Hook Handlers

    def on_project_analyzed(self, context: PluginContext):
        """Called after project is analyzed"""
        if not self.auto_sync:
            return

        project = context.project
        if not project:
            return

        project_name = project["name"]
        logger.info(f"🐙 GitHub plugin: Syncing data for '{project_name}'")

        # Try to detect GitHub repo from git remote
        repo_info = self._detect_repo(project)
        if not repo_info:
            logger.debug(f"No GitHub repository detected for '{project_name}'")
            return

        # Sync repository metadata
        self._sync_repo_metadata(context, repo_info)

        # Sync issues
        if self.sync_issues:
            self._sync_issues(context, repo_info)

        # Sync pull requests
        if self.sync_prs:
            self._sync_pull_requests(context, repo_info)

    def on_session_created(self, context: PluginContext):
        """Called after session is created"""
        if not self.create_issues_from_sessions or not self.token:
            return

        # Check if session has accomplishments that should become issues
        accomplishments = context.get_data("accomplishments", [])
        if not accomplishments:
            return

        # Look for TODO markers or action items
        for accomplishment in accomplishments:
            if "TODO:" in accomplishment or "FIXME:" in accomplishment:
                logger.info(f"📝 Found potential issue in accomplishment: {accomplishment[:50]}...")
                # Could automatically create issue here

    # GitHub API Methods

    def _make_request(
        self, endpoint: str, method: str = "GET", data: Dict = None
    ) -> Optional[Dict]:
        """
        Make GitHub API request

        Args:
            endpoint: API endpoint (relative to API_BASE)
            method: HTTP method
            data: Request data for POST/PUT

        Returns:
            Response JSON or None if failed
        """
        url = f"{self.API_BASE}/{endpoint}"
        headers = {"Accept": "application/vnd.github.v3+json"}

        if self.token:
            headers["Authorization"] = f"token {self.token}"

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.error(f"❌ GitHub resource not found: {endpoint}")
            elif e.response.status_code == 403:
                logger.error(f"❌ GitHub API rate limit exceeded or access denied")
            else:
                logger.error(f"❌ GitHub API error: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to make GitHub request: {e}")
            return None

    def _detect_repo(self, project: Dict) -> Optional[Dict]:
        """
        Detect GitHub repository from project

        Args:
            project: Project dict

        Returns:
            Dict with 'owner' and 'repo' keys, or None
        """
        # Check project context for GitHub info
        # (Could be set manually or from previous sync)
        # For now, try to parse from git remote

        project_dir = project.get("directory")
        if not project_dir:
            return None

        try:
            import subprocess

            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return None

            remote_url = result.stdout.strip()

            # Parse GitHub URL
            # Examples:
            #   https://github.com/owner/repo.git
            #   git@github.com:owner/repo.git
            if "github.com" not in remote_url:
                return None

            if remote_url.startswith("git@"):
                # git@github.com:owner/repo.git
                parts = remote_url.split(":")[1].replace(".git", "").split("/")
            else:
                # https://github.com/owner/repo.git
                parts = remote_url.replace("https://", "").replace(".git", "").split("/")[-2:]

            if len(parts) >= 2:
                return {"owner": parts[0], "repo": parts[1]}

        except Exception as e:
            logger.debug(f"Failed to detect GitHub repo: {e}")

        # Fall back to config defaults
        owner = self.config.get("repo_owner")
        repo = self.config.get("repo_name")
        if owner and repo:
            return {"owner": owner, "repo": repo}

        return None

    def _sync_repo_metadata(self, context: PluginContext, repo_info: Dict):
        """Sync repository metadata to context"""
        endpoint = f"repos/{repo_info['owner']}/{repo_info['repo']}"
        data = self._make_request(endpoint)

        if not data:
            return

        # Store useful metadata in context
        if context.memory and context.project:
            project_id = context.project["id"]

            # Update project description if empty
            if data.get("description") and not context.project.get("description"):
                logger.info(f"📝 Updating project description from GitHub")
                # Would call context.memory.db.update_project() here

            # Store GitHub metadata
            github_meta = {
                "owner": repo_info["owner"],
                "repo": repo_info["repo"],
                "full_name": data.get("full_name"),
                "description": data.get("description"),
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "topics": data.get("topics", []),
                "language": data.get("language"),
                "default_branch": data.get("default_branch"),
                "url": data.get("html_url"),
                "last_synced": datetime.now().isoformat(),
            }

            # Store in context
            for key, value in github_meta.items():
                if value is not None:
                    context.memory.db.set_context(project_id, "github", key, str(value))

            logger.info(f"✅ Synced GitHub metadata: {data.get('full_name')}")

    def _sync_issues(self, context: PluginContext, repo_info: Dict):
        """Sync GitHub issues to context"""
        endpoint = f"repos/{repo_info['owner']}/{repo_info['repo']}/issues"
        issues = self._make_request(endpoint)

        if not issues:
            return

        # Filter out pull requests (GitHub API includes PRs in issues endpoint)
        issues = [issue for issue in issues if "pull_request" not in issue]

        if context.memory and context.project:
            project_id = context.project["id"]

            # Store issue count
            context.memory.db.set_context(
                project_id,
                "github",
                "open_issues",
                str(len([i for i in issues if i["state"] == "open"])),
            )

            # Store recent issues
            for i, issue in enumerate(issues[:5]):  # Limit to 5 most recent
                issue_key = f"recent_issue_{i+1}"
                issue_summary = f"#{issue['number']}: {issue['title']} [{issue['state']}]"
                context.memory.db.set_context(project_id, "github", issue_key, issue_summary)

            logger.info(f"✅ Synced {len(issues)} GitHub issues")

    def _sync_pull_requests(self, context: PluginContext, repo_info: Dict):
        """Sync GitHub pull requests to context"""
        endpoint = f"repos/{repo_info['owner']}/{repo_info['repo']}/pulls"
        prs = self._make_request(endpoint)

        if not prs:
            return

        if context.memory and context.project:
            project_id = context.project["id"]

            # Store PR count
            context.memory.db.set_context(
                project_id,
                "github",
                "open_prs",
                str(len([pr for pr in prs if pr["state"] == "open"])),
            )

            # Store recent PRs
            for i, pr in enumerate(prs[:3]):  # Limit to 3 most recent
                pr_key = f"recent_pr_{i+1}"
                pr_summary = (
                    f"#{pr['number']}: {pr['title']} [{pr['state']}] by {pr['user']['login']}"
                )
                context.memory.db.set_context(project_id, "github", pr_key, pr_summary)

            logger.info(f"✅ Synced {len(prs)} GitHub pull requests")

    # Custom Commands

    def sync_github(self, project_name: str = None):
        """Manually trigger GitHub sync for a project"""
        if not project_name:
            logger.error(
                "❌ Project name required: recall --plugin-command github:sync project-name"
            )
            return

        from recall_lib.project_memory import ProjectMemory

        memory = ProjectMemory()

        project = memory.db.get_project(project_name)
        if not project:
            logger.error(f"❌ Project '{project_name}' not found")
            return

        logger.info(f"🔄 Syncing GitHub data for '{project_name}'...")

        # Create context and trigger sync
        context = PluginContext(memory=memory, project=project)
        self.on_project_analyzed(context)

    def list_issues(self, project_name: str = None):
        """List GitHub issues for a project"""
        if not project_name:
            logger.error(
                "❌ Project name required: recall --plugin-command github:issues project-name"
            )
            return

        from recall_lib.project_memory import ProjectMemory

        memory = ProjectMemory()

        project = memory.db.get_project(project_name)
        if not project:
            logger.error(f"❌ Project '{project_name}' not found")
            return

        repo_info = self._detect_repo(project)
        if not repo_info:
            logger.error(f"❌ No GitHub repository detected for '{project_name}'")
            return

        logger.info(f"🐙 Fetching issues for {repo_info['owner']}/{repo_info['repo']}...\n")

        endpoint = f"repos/{repo_info['owner']}/{repo_info['repo']}/issues"
        issues = self._make_request(endpoint)

        if not issues:
            logger.info("No issues found")
            return

        # Filter out PRs
        issues = [issue for issue in issues if "pull_request" not in issue]

        for issue in issues[:10]:  # Show first 10
            state_emoji = "🟢" if issue["state"] == "open" else "🔴"
            logger.info(f"{state_emoji} #{issue['number']}: {issue['title']}")
            logger.info(f"   Labels: {', '.join([l['name'] for l in issue.get('labels', [])])}")
            logger.info(f"   URL: {issue['html_url']}\n")

    def list_prs(self, project_name: str = None):
        """List GitHub pull requests for a project"""
        if not project_name:
            logger.error(
                "❌ Project name required: recall --plugin-command github:prs project-name"
            )
            return

        from recall_lib.project_memory import ProjectMemory

        memory = ProjectMemory()

        project = memory.db.get_project(project_name)
        if not project:
            logger.error(f"❌ Project '{project_name}' not found")
            return

        repo_info = self._detect_repo(project)
        if not repo_info:
            logger.error(f"❌ No GitHub repository detected for '{project_name}'")
            return

        logger.info(f"🐙 Fetching PRs for {repo_info['owner']}/{repo_info['repo']}...\n")

        endpoint = f"repos/{repo_info['owner']}/{repo_info['repo']}/pulls"
        prs = self._make_request(endpoint)

        if not prs:
            logger.info("No pull requests found")
            return

        for pr in prs[:10]:  # Show first 10
            state_emoji = "🟢" if pr["state"] == "open" else "🔴"
            logger.info(f"{state_emoji} #{pr['number']}: {pr['title']}")
            logger.info(f"   Author: {pr['user']['login']}")
            logger.info(f"   Branch: {pr['head']['ref']} → {pr['base']['ref']}")
            logger.info(f"   URL: {pr['html_url']}\n")

    def show_repo_info(self, project_name: str = None):
        """Show GitHub repository information"""
        if not project_name:
            logger.error(
                "❌ Project name required: recall --plugin-command github:repo-info project-name"
            )
            return

        from recall_lib.project_memory import ProjectMemory

        memory = ProjectMemory()

        project = memory.db.get_project(project_name)
        if not project:
            logger.error(f"❌ Project '{project_name}' not found")
            return

        repo_info = self._detect_repo(project)
        if not repo_info:
            logger.error(f"❌ No GitHub repository detected for '{project_name}'")
            return

        endpoint = f"repos/{repo_info['owner']}/{repo_info['repo']}"
        data = self._make_request(endpoint)

        if not data:
            return

        logger.info(f"📦 {data['full_name']}")
        logger.info(f"   {data.get('description', 'No description')}\n")
        logger.info(f"⭐ Stars: {data.get('stargazers_count', 0)}")
        logger.info(f"🍴 Forks: {data.get('forks_count', 0)}")
        logger.info(f"👁️ Watchers: {data.get('watchers_count', 0)}")
        logger.info(f"📂 Language: {data.get('language', 'Unknown')}")
        logger.info(f"🏷️  Topics: {', '.join(data.get('topics', []))}")
        logger.info(f"🌐 URL: {data['html_url']}")

    def create_issue(self, project_name: str = None, title: str = None, body: str = None):
        """Create a GitHub issue"""
        if not self.token:
            logger.error("❌ GitHub token required to create issues")
            return

        if not project_name or not title:
            logger.error(
                "❌ Usage: recall --plugin-command github:create-issue project-name 'title' 'body'"
            )
            return

        from recall_lib.project_memory import ProjectMemory

        memory = ProjectMemory()

        project = memory.db.get_project(project_name)
        if not project:
            logger.error(f"❌ Project '{project_name}' not found")
            return

        repo_info = self._detect_repo(project)
        if not repo_info:
            logger.error(f"❌ No GitHub repository detected for '{project_name}'")
            return

        endpoint = f"repos/{repo_info['owner']}/{repo_info['repo']}/issues"
        data = {"title": title, "body": body or ""}

        result = self._make_request(endpoint, method="POST", data=data)
        if result:
            logger.info(f"✅ Created issue #{result['number']}: {result['title']}")
            logger.info(f"🌐 {result['html_url']}")


# Allow standalone testing
if __name__ == "__main__":
    # Test the plugin
    config = {
        "auto_sync": True,
        "sync_issues": True,
        "sync_prs": True,
    }

    plugin = GitHubPlugin(config=config)
    print(f"Plugin: {plugin.name} v{plugin.version}")
    print(f"Description: {plugin.description}")
    print(f"\nConfig Schema:")
    for key, spec in plugin.get_config_schema().items():
        print(f"  {key}: {spec['description']}")

    print(f"\nInitializing...")
    if plugin.initialize():
        print("✅ Plugin initialized successfully")

        print(f"\nRegistered Commands:")
        for cmd in plugin.get_commands().keys():
            print(f"  - github:{cmd}")
    else:
        print("❌ Plugin initialization failed")
