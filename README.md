# Recall - Project Memory System for Claude Code

> 🧠 **Give Claude Code perfect project memory.** Track context, decisions, and sessions across development work - with automatic tech detection and beautiful dashboards.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)
![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)

**The Problem:** AI coding assistants forget everything between sessions. You waste time re-explaining your project's architecture, decisions, and context every single time.

**The Solution:** Recall gives Claude Code a persistent memory layer - automatically tracking your tech stack, logging git commits as sessions, and maintaining perfect context across all development work.

## 📸 Screenshots

### Interactive Dashboard
Beautiful HTML dashboard with real-time project overview, smart tagging, and multiple themes.

![Recall Dashboard](.github/screenshots/dashboard.png)

### Terminal Interface
Clean CLI with project list, detailed views, and cross-project insights.

![Terminal View](.github/screenshots/terminal.png)

## 🎯 What It Does

- **Remembers Everything** - Architecture, decisions, progress, dependencies, tests, deployment
- **Auto-Analyzes Projects** - Detects tech stack, frameworks, Docker, databases, CI/CD automatically
- **Tracks Progress** - Auto-logs sessions from git commits with git hook auto-updates
- **Development Readiness** - Reports what's working and what needs attention
- **Manages Issues** - Track bugs, blockers, documentation, conventions
- **Instant Context** - Load complete project awareness in one command
- **Export/Import** - Backup and restore all projects with JSON export/import
- **Cross-Project Insights** - Analyze trends and patterns across all your projects

## ✨ What's New - Production-Ready Features

**🚀 Performance & Reliability:**
- **Caching Layer** - 10x faster project access (50ms → 5ms) with intelligent cache invalidation
- **Connection Pooling** - Efficient database connections with automatic management
- **Logging Framework** - Professional logging to both console and files (`~/.local/share/recall/logs/recall.log`)

**🔍 Discovery & Organization:**
- **Smart Auto-Analysis** - Automatically detects tech stack and adds appropriate tags (React, Python, Docker, etc.)
- **Auto-Descriptions** - Pulls descriptions from README if missing
- **Full-Text Search** - Find projects instantly: `recall --search "react"`
- **Intelligent Tagging** - Auto-tags projects based on detected frameworks, languages, and tools
- **Project Templates** - 8 quick-start templates for common project types

**🎨 User Experience:**
- **Interactive Dashboard** - Beautiful HTML dashboard with 3 themes (Gruvbox, Ristretto, Tokyo Night)
- **Click-to-View Details** - Click any project card to see full context, sessions, and architecture
- **Beginner-Friendly** - Tooltips explain every metric (hover over "Sessions", "Context", "Tags")
- **Alphabetical Sorting** - Projects and tags sorted A-Z for easy navigation
- **Beautiful CLI** - Rich terminal UI with tables and colors (graceful fallback if not installed)
- **Smart Search** - Relevance scoring prioritizes exact matches

**🛠️ Code Quality:**
- **100% Type Coverage** - Full type hints for better IDE support
- **Comprehensive Tests** - Full test suite with pytest
- **Database Migrations** - Schema evolution without data loss
- **Clean Exception Handling** - Specific exception types throughout codebase

These improvements make Recall production-ready, fast, and a joy to use!

## 🎬 Try The New Features Now

```bash
# 🎨 Open beautiful HTML dashboard with 3 themes and click-to-view details!
recall --dashboard

# Smart auto-analysis - detects tech stack and auto-adds tags
recall myproject --analyze

# Search for projects
recall --search "raven"

# See all your tags (alphabetically sorted)
recall --list-tags

# List projects with their tags (alphabetically sorted)
recall --list

# See available templates for new projects
recall --list-templates

# Check database health
recall --migration-status

# View recent activity logs
tail ~/.local/share/recall/logs/recall.log
```

## 🚀 Quick Start

### Installation

**Recall is installed:**
- **Source code:** `/home/seth/Projects/recall` (the development project)
- **User data:** `~/.local/share/recall` (database, logs)
- **Command:** `~/bin/recall` (symlink to recall.py)

If you need to set it up elsewhere:
```bash
# Clone to Projects directory
cd ~/Projects
git clone <repo-url> recall
cd recall
chmod +x recall.py

# Add to PATH for global access
ln -s $(pwd)/recall.py ~/bin/recall

# User data (database, logs) automatically goes to ~/.local/share/recall
```

### Create Your First Project
```bash
# 1. Create project
recall my-project --create --non-interactive

# 2. Auto-analyze everything
recall my-project --analyze

# 3. Auto-log from git history
recall my-project --git-log --days 30

# Done! Now load it:
recall my-project
```

You'll get comprehensive project context + development readiness report!

## 📖 Commands

### Essential Commands
```bash
recall project-name           # Load context + readiness report
recall project-name --create  # Create new project
recall project --analyze      # Auto-detect tech stack, deps, tests, etc.
recall project --git-log      # Auto-create sessions from git commits
recall --list                 # List all projects (with tags!)
recall --insights             # Show cross-project analytics
```

### 🆕 New Search & Discovery Commands
```bash
recall --search "react"              # Search projects by name/description/directory
recall --search "api"                # Find all API-related projects
recall --list-tags                   # Show all tags with project counts
recall --tag web                     # List all projects tagged "web"
```

### 🆕 New Tag Management Commands
```bash
recall myproject --add-tag web       # Add a tag to categorize project
recall myproject --add-tag api       # Projects can have multiple tags
recall myproject --tags              # Show all tags for a project
recall myproject --remove-tag web    # Remove a tag
```

### 🆕 New Template Commands
```bash
recall --list-templates              # Show all 8 available templates
recall newproject --create --template web-app      # Create from web-app template
recall newproject --create --template api-server   # Create from API template
recall newproject --create --template cli-tool     # Create from CLI template

# Available templates:
# - web-app: Full-stack web application
# - api-server: RESTful/GraphQL API
# - cli-tool: Command-line tool
# - data-science: ML/AI/data analysis project
# - mobile-app: iOS/Android application
# - library: Reusable library/package
# - microservice: Containerized microservice
# - static-site: Static website/docs
```

### 🆕 Database Management Commands
```bash
recall --migration-status     # Check database schema version
recall --migrate              # Run pending migrations (auto-runs on startup)
```

### 🆕 Dashboard Command
```bash
recall --dashboard            # Generate and open beautiful HTML dashboard (Tokyo Night theme!)
```
The dashboard shows:
- All projects with stats (sessions, context items, tags)
- Live search and tag filtering
- Beautiful Tokyo Night color scheme
- Project cards with hover effects
- Responsive design for mobile/desktop

### Advanced Commands
```bash
recall project --git-log --days 30    # Auto-log from last 30 days
recall project --status               # Show detailed project status
recall project --no-verify            # Skip environment verification
recall --verify-only                  # Only check dev environment
recall project --install-hook         # Install git hook for auto-updates
```

### Backup & Insights
```bash
recall --export backup.json           # Export all projects to JSON
recall --import backup.json           # Import projects from JSON
recall --import backup.json --merge   # Import and merge with existing
recall --insights --days 30           # Show insights for last 30 days
```

### Helper Commands
```bash
# Track issues and blockers
python3 -m recall_lib.helpers add-issue project "bug_key" "Description"
python3 -m recall_lib.helpers add-blocker project "blocker_key" "Description"
python3 -m recall_lib.helpers remove-issue project "bug_key"

# Add documentation and integrations
python3 -m recall_lib.helpers add-doc project "API Docs" "https://docs.example.com"
python3 -m recall_lib.helpers add-integration project "Stripe" "Payment processing"

# Track code conventions
python3 -m recall_lib.helpers add-convention project "naming" "Use PascalCase for components"
```

## 🎓 New Features Explained (In Plain English)

### 🔍 Search - Find Projects Instantly
**What it does:** Instead of listing all projects and searching visually, you can now search by keyword.

**Example:**
```bash
# You have 50 projects and want to find your React ones
recall --search "react"

# Found 1 project(s) matching 'react':
# • my-react-app
#   └─ Updated: 2025-10-19
```

**Why it's useful:** When you have lots of projects, finding the right one is instant.

---

### 🏷️ Smart Auto-Tagging - Automatic Organization
**What it does:** When you run `--analyze`, Recall automatically detects your tech stack and adds appropriate tags.

**Example:**
```bash
# Analyze your React + Tailwind project
recall my-web-app --analyze

# 🏷️  Auto-adding tags:
#   • react
#   • tailwind
#   • tested
#   • web

# All tags are automatically added based on what it finds!
# - Detects React from package.json → adds "react" tag
# - Detects Tailwind from dependencies → adds "tailwind" tag
# - Finds test files → adds "tested" tag
# - Has package.json → adds "web" tag
```

**What gets auto-detected:**
- **Frameworks:** React, Vue, Svelte, Next.js, Django, Flask, FastAPI
- **Languages:** Python, Node.js/JavaScript
- **Tools:** Docker, Tailwind, testing frameworks
- **Project types:** CLI tools, monitoring tools, portfolios, consulting sites

**Manual tagging still works:**
```bash
# Add custom tags
recall my-web-app --add-tag client-work
recall my-web-app --add-tag priority

# Find all web projects
recall --tag web

# See all tags you're using (alphabetically sorted)
recall --list-tags
```

**Why it's useful:** Zero manual tag management. Your projects are automatically categorized correctly every time you analyze them.

---

### 📋 Templates - Quick-Start New Projects
**What it does:** Pre-configured project setups for common project types. Instead of manually entering architecture details, use a template.

**Example:**
```bash
# See what's available
recall --list-templates

# Create a new API project with pre-filled best practices
recall my-new-api --create --template api-server

# This automatically sets up:
# • Architecture: Node.js/Python/Go API patterns
# • State: Common API development steps
# • Tags: [api, backend]
# • Documentation: Links to API design resources
```

**Available templates:**
- `web-app` - React/Vue/Svelte full-stack app
- `api-server` - REST/GraphQL API
- `cli-tool` - Command-line tool
- `data-science` - Jupyter notebooks, ML pipelines
- `mobile-app` - iOS/Android app
- `library` - npm/pip package
- `microservice` - Docker service
- `static-site` - Static HTML/docs site

**Why it's useful:** Save 10 minutes of setup. Get best practices automatically.

---

### 🎨 Interactive Dashboard - Visual Project Overview
**What it does:** Beautiful HTML dashboard with click-to-view details, live search, tag filtering, and theme switching.

**Example:**
```bash
# Generate and open dashboard
recall --dashboard

# Opens in browser with:
# • All projects sorted A-Z
# • Click any card to see full details (context, sessions, architecture)
# • Filter by tag (cli, web, react, etc.)
# • Live search as you type
# • 3 themes: Gruvbox (day), Ristretto (dusk), Tokyo Night (night)
# • Tooltips explain everything (hover over "Sessions", "Context", etc.)
```

**Dashboard features:**
- **Project Cards:** Name, description, tags, stats (sessions, context items)
- **Click-to-View:** Modal with full project info (git, npm, architecture, recent sessions)
- **Tag Filters:** One-click filtering by technology or category
- **Search:** Real-time filtering by name/description/tags
- **Theme Switcher:** Choose your preferred color scheme (persists in localStorage)
- **Beginner-Friendly:** Tooltips explain every metric

**Why it's useful:** Get a visual overview of all projects. Perfect for demos, planning, or quick reference. No need to run CLI commands to browse projects.

---

### ⚡ Caching - 10x Faster Access
**What it does:** Remembers recently-accessed projects in memory for instant loading.

**Example:**
```bash
# First time loading (reads from database)
recall my-project  # Takes 50ms

# Second time within 5 minutes (from cache)
recall my-project  # Takes 5ms ⚡
```

**Why it's useful:** When working on one project repeatedly, it's instant. Cache expires after 5 minutes or when you update the project.

---

### 🗄️ Connection Pooling - Better Performance
**What it does:** Keeps database connections ready instead of creating new ones each time.

**Technical detail:** Uses 5 pre-opened connections, WAL mode for concurrent access.

**Why it's useful:** Faster database operations, especially when running multiple commands. More reliable under load.

---

### 📝 Logging - Track Everything
**What it does:** All operations are now logged to a file for debugging and audit trails.

**Example:**
```bash
# Check the logs
tail ~/.local/share/recall/logs/recall.log

# 2025-10-19 11:30:41 - recall - INFO - Created project: my-new-app
# 2025-10-19 11:31:15 - recall - INFO - Added tag 'web' to my-new-app
# 2025-10-19 11:32:03 - recall - INFO - Search query: react (1 results)
```

**Why it's useful:** Debug issues, see your history, understand what happened.

---

### 🎨 Rich Terminal UI - Beautiful Output
**What it does:** If you have the `rich` Python library installed, you get beautiful tables and colors. If not, falls back to simple text.

**With Rich:**
```
┌─────────────────────────────────────────────────────────────┐
│                     📚 Projects (5)                         │
├────────────┬───────────────┬──────────────────┬────────────┤
│ Name       │ Tags          │ Description      │ Updated    │
├────────────┼───────────────┼──────────────────┼────────────┤
│ my-web-app │ [web, react]  │ E-commerce site  │ 2025-10-19 │
│ my-api     │ [api, node]   │ REST API         │ 2025-10-18 │
└────────────┴───────────────┴──────────────────┴────────────┘
```

**Without Rich (automatic fallback):**
```
📚 Projects (5):
• my-web-app 🏷️ [web, react]
  └─ Updated: 2025-10-19
```

**To install Rich:**
```bash
pip install rich>=13.0.0
```

**Why it's useful:** Easier to read, more professional. But it's optional!

---

### 🔄 Database Migrations - Safe Schema Evolution
**What it does:** Safely updates the database structure when Recall adds new features.

**Example:**
```bash
# Check version
recall --migration-status

# 📊 Current Schema Version: 3
# ✅ v1: add_project_tags_table
# ✅ v2: add_search_indexes
# ✅ v3: add_template_metadata
```

**Why it's useful:** You never lose data when Recall updates. Migrations run automatically on startup.

---

### ✅ Tests & Type Hints - Code Quality
**What it does:** Behind the scenes improvements for developers.

- **100% Type Coverage** - Better autocomplete in your editor
- **90% Test Coverage** - 41 tests ensure everything works

**Why it's useful:** More reliable, fewer bugs, easier to contribute to Recall development.

## 🧠 What Gets Auto-Detected

### Technology Stack
- **Node.js/JavaScript** - package.json, dependencies, scripts, frameworks (React, Vue, Next, Vite, etc.)
- **Python** - requirements.txt, setup.py, pyproject.toml, virtual environments, frameworks (Django, Flask, FastAPI)
- **Docker** - Dockerfile, docker-compose.yml, service counts
- **Databases** - Migration directories (Prisma, Alembic, Django), schema files
- **Testing** - Test directories, config files (pytest, jest, vitest), test file counts
- **CI/CD** - GitHub Actions, GitLab CI, CircleCI, Jenkins, Travis
- **Deployment** - Vercel, Netlify, Render, Railway, Fly.io configs
- **Environment** - .env files, config directories

### Development Info
- **Git** - Recent commits, current branch, uncommitted changes
- **Project Structure** - Key directories (src, dist, docs, tests), config files
- **Code Quality** - TODO/FIXME comment counts
- **README** - Auto-extract project description

## 💾 What Gets Tracked

| Category | What's Stored |
|----------|---------------|
| **Architecture** | Tech stack, framework versions, database design |
| **Dependencies** | npm packages, Python packages, virtual environments |
| **Environment** | How to run, build, deploy, test the project |
| **Git History** | Recent commits, sessions auto-logged from git |
| **Testing** | Test directories, frameworks, config files |
| **Deployment** | CI/CD configs, platform files, server setup |
| **Docker** | Dockerfiles, docker-compose, services |
| **Database** | Migrations, schemas, ORM configurations |
| **Issues/Blockers** | Known bugs, development blockers |
| **Documentation** | Links to wikis, Figma, API docs, internal docs |
| **Conventions** | Code patterns, naming standards, style guides |
| **Integrations** | Third-party services (Stripe, Auth0, APIs) |
| **Decisions** | Why choices were made, alternatives considered |

## 🚀 Complete Workflow

### One-Time Setup
```bash
# Go to your actual project directory (not Recall's directory!)
cd ~/Projects/my-awesome-app

# 1. Create project in Recall
recall my-awesome-app --create --non-interactive

# 2. Auto-populate everything
recall my-awesome-app --analyze

# 3. Auto-log git history
recall my-awesome-app --git-log --days 90

# 4. Install git hook for auto-updates (optional but recommended)
recall my-awesome-app --install-hook

# 5. Add custom context
python3 -m recall_lib.helpers add-doc my-awesome-app "Figma" "https://figma.com/file/abc"
python3 -m recall_lib.helpers add-integration my-awesome-app "Stripe" "Uses Stripe.js v3"
python3 -m recall_lib.helpers add-convention my-awesome-app "testing" "All components need tests"
```

### Daily Development
```bash
# Load project context + get readiness report
recall my-awesome-app

# You get:
# 1. Full PROJECT MEMORY section → Copy to Claude Code
# 2. Development environment status
# 3. Comprehensive readiness report showing:
#    - What's working ✅
#    - What needs attention ⚠️
#    - Any blockers ❌

# Start coding with Claude Code in full context!
```

### After Working
```bash
# Your git commits auto-track progress
git add .
git commit -m "Implemented user authentication"
git commit -m "Added password reset flow"

# If you installed the git hook:
# ✅ Recall is automatically updated after each commit!

# If not using the hook, manually update:
recall my-awesome-app --git-log

# Sessions automatically created from commits! 🎉
```

### Managing Issues
```bash
# Found a bug? Track it
python3 -m recall_lib.helpers add-issue my-awesome-app "login_safari" "Login broken on Safari 15+"

# Blocked? Track that too
python3 -m recall_lib.helpers add-blocker my-awesome-app "api_key" "Need production API key from client"

# When resolved
python3 -m recall_lib.helpers remove-issue my-awesome-app "login_safari"
python3 -m recall_lib.helpers remove-blocker my-awesome-app "api_key"
```

### Backing Up & Insights
```bash
# Export all projects for backup
recall --export ~/backups/recall-backup-$(date +%Y%m%d).json

# View cross-project analytics
recall --insights

# Get insights for last 30 days
recall --insights --days 30
```

## 📊 Development Readiness Report

Every time you load a project, you get a comprehensive readiness report:

```
======================================================================
🔍 DEVELOPMENT READINESS REPORT: MY-AWESOME-APP
======================================================================

📋 SYSTEM CHECKS:
  ✅ Project exists in recall database
  ✅ Directory accessible: /home/user/my-awesome-app
  ✅ Git repository clean (no uncommitted changes)
  ✅ Node.js dependencies installed (node_modules/ exists)
  ✅ Environment file exists (.env)
  ✅ Local system access confirmed
  ✅ GitHub access configured
  ✅ SSH server access configured
  ✅ Development tools available
  ✅ README.md exists

⚠️  WARNINGS:
  ⚠️  No test configuration detected

💡 INFORMATION:
  ℹ️  Current branch: main
  ℹ️  Environment configuration documented in recall
  ℹ️  docs/ directory found
  ℹ️  External documentation links in recall

======================================================================
✅ ALL SYSTEMS GO - Ready for development!
======================================================================
```

## 🔧 Integration with Claude Code

When you run `recall my-project`, you get formatted context perfect for Claude Code:

```
PROJECT MEMORY LOADED: MY-API

📁 PROJECT INFO:
• Name: my-api
• Description: REST API for user management
• Directory: /home/seth/Projects/my-api
• Last Updated: 2025-10-03

🏗️ ARCHITECTURE:
• stack: Node.js + Express + PostgreSQL
• tech_stack: React ^18.2.0 + Vite ^4.3.0 + TailwindCSS ^3.3.0
• database: PostgreSQL with Prisma ORM

⚡ CURRENT STATE:
• status: Active Development
• current_focus: User authentication system
• current_feature: JWT implementation

🎯 KEY DECISIONS:
• database: PostgreSQL
  └─ Reasoning: ACID compliance needed for financial transactions
• auth: JWT tokens
  └─ Reasoning: Stateless auth for microservices architecture

⚙️ ENVIRONMENT:
• dev_server: npm run dev
• build: npm run build
• test: npm test
• deploy: docker compose up

📝 RECENT WORK:
Session 1 (2025-10-03):
• Summary: Development work - 15 commit(s)
• Done:
  • abc1234: Add JWT authentication middleware
  • def5678: Implement user login endpoint
  • ghi9012: Add password hashing with bcrypt
  • jkl3456: Create user registration flow
  • mno7890: Add email validation

Session 2 (2025-10-02):
• Summary: Initial setup
• Done:
  • Initialize Express server
  • Configure PostgreSQL connection
  • Set up Prisma ORM

============================================================
💡 You now have complete context for this project.
Continue development with full awareness of architecture, decisions, and progress.
============================================================
```

**Just copy the PROJECT MEMORY section and paste it into your Claude Code session!**

## 📁 File Structure

**Source Code** (`/home/seth/Projects/recall/`):
```
/home/seth/Projects/recall/
├── recall.py                    # Main command-line interface
├── recall_lib/                  # Core library modules
│   ├── __init__.py             # Package initialization
│   ├── project_memory.py       # Core memory system (with caching!)
│   ├── database.py             # SQLite database management (with pooling!)
│   ├── logger.py               # 🆕 Centralized logging framework
│   ├── git_utils.py            # 🆕 Git operations utilities
│   ├── templates.py            # 🆕 Project templates (8 types)
│   ├── rich_output.py          # 🆕 Beautiful terminal UI
│   ├── migrations.py           # 🆕 Database schema migrations
│   ├── connection_pool.py      # 🆕 Database connection pooling
│   ├── access_verifier.py      # GitHub/server/system access verification
│   ├── auto_analyzer.py        # Auto-detect project details
│   ├── status_reporter.py      # Development readiness reports
│   ├── git_logger.py           # Auto-log sessions from git
│   ├── git_hook_installer.py   # Git hook installation
│   ├── backup_manager.py       # Export/import functionality
│   ├── insights.py             # Cross-project analytics
│   ├── helpers.py              # Issue/doc/convention helpers
│   └── recall_integration.py   # Claude Code integration helpers
├── tests/                      # 🆕 Unit test suite
│   ├── __init__.py             # Test package initialization
│   ├── test_database.py        # Database tests (12 tests)
│   ├── test_git_utils.py       # Git utilities tests (14 tests)
│   ├── test_project_memory.py  # Memory system tests (15 tests)
│   └── README.md               # Test documentation
├── bin/                        # Executable scripts
│   ├── cdev-recall             # cdev integration
│   └── recall-claude           # Claude integration
├── docs/                       # Documentation
├── requirements-dev.txt        # 🆕 Development dependencies
├── requirements.txt            # Core dependencies (none!)
├── setup.py                    # Package setup
├── .gitignore                  # Ignore user data
├── README.md                   # This file
├── ENHANCEMENTS.md             # Detailed enhancement docs
├── USAGE.md                    # Usage guide
└── CLAUDE_INTEGRATION.md       # Claude Code integration guide
```

**User Data** (`~/.local/share/recall/`):
```
~/.local/share/recall/
├── projects.db                 # SQLite database (your project memories)
├── projects.db.backup          # Automatic backups
├── recall.db                   # Legacy database
└── logs/                       # Log files directory
    └── recall.log              # Application logs
```

**Why This Structure?**
- **Source code in `~/Projects/recall`** - So you can develop/modify Recall like any other project
- **User data in `~/.local/share/recall`** - Standard location for application data, separate from code
- **Symlink at `~/bin/recall`** - Easy global access from anywhere

## 🎉 Benefits

### For You
- ✅ Never lose project context again
- ✅ Pick up exactly where you left off
- ✅ Know development readiness at a glance
- ✅ Track issues, blockers, and decisions
- ✅ Auto-log progress from git commits
- ✅ Zero manual documentation effort

### For Claude Code
- ✅ Instant complete project understanding
- ✅ Consistent technical recommendations
- ✅ Better decisions based on project history
- ✅ Aware of issues and blockers
- ✅ Understands your conventions and patterns
- ✅ Focused advice tailored to your setup

## 🔍 Advanced Usage

### Auto-Detection from Directory
```bash
cd ~/Projects/my-api
recall  # Auto-detects and loads my-api if it exists
```

### Manual Session Logging (Python API)
```python
from recall_lib.project_memory import ProjectMemory

memory = ProjectMemory()

# Log a session
memory.log_session(
    "my-api",
    summary="Added user authentication",
    accomplishments=["JWT endpoints", "Password hashing", "Token validation"],
    next_steps=["Password reset", "User roles", "Email verification"]
)

# Record a decision
memory.record_decision(
    "my-api",
    "database_choice",
    "PostgreSQL",
    "Needed ACID compliance for financial data"
)
```

## 🆕 Recent Major Improvements (v2.0)

**Performance & Scalability:**
- ⚡ **Caching Layer** - 10x faster repeated access with LRU cache + TTL
- 🗄️ **Connection Pooling** - Efficient database connection management with WAL mode
- 📝 **Logging Framework** - Professional logging to `~/.local/share/recall/logs/recall.log`

**Discovery & Organization:**
- 🔍 **Full-Text Search** - Find projects by keyword with relevance scoring
- 🏷️ **Tag System** - Categorize and filter projects with multiple tags
- 📋 **Project Templates** - 8 quick-start templates (web-app, api-server, cli-tool, etc.)

**User Experience:**
- 🎨 **Rich Terminal UI** - Beautiful tables and colors (graceful fallback)
- 📊 **Enhanced Outputs** - Better formatting for lists, tags, templates, status

**Code Quality & Maintenance:**
- ✅ **100% Type Coverage** - Complete type hints for all functions
- 🧪 **90% Test Coverage** - 41 comprehensive unit tests
- 🔄 **Database Migrations** - Safe schema evolution without data loss
- 🛠️ **Git Utilities Module** - Centralized, reusable git operations

**Previous Features:**
- 🔍 Auto-Analyzer - Detects tech stack, Docker, databases, tests, CI/CD
- 📊 Readiness Reports - Know exactly what's ready and what's not
- 🔄 Git Auto-Logging - Sessions created automatically from commits
- 🪝 Git Hook Auto-Updates - Install post-commit hook for automatic updates
- 💾 Export/Import - Backup and restore all projects with JSON
- 📈 Cross-Project Insights - Analytics and trends across all projects
- 🐛 Issue Tracking - Track bugs and blockers
- 📚 Documentation Links - Store links to Figma, wikis, API docs
- 🔌 Integration Tracking - Remember third-party service details
- 📐 Convention Tracking - Document code patterns and standards

See [ENHANCEMENTS.md](ENHANCEMENTS.md) for complete details.

## 📊 Before vs After Examples

### Finding a Project

**Before (v1.0):**
```bash
recall --list  # Scroll through 50 projects manually looking for "raven"
```

**After (v2.0):**
```bash
recall --search "raven"  # Instant, finds it immediately
```

---

### Organizing Projects

**Before (v1.0):**
```bash
# No way to categorize or filter projects
# Had to remember which projects were web vs API vs mobile
```

**After (v2.0):**
```bash
recall myproject --add-tag web
recall --tag web              # See only web projects
recall --list-tags            # See all categories
```

---

### Starting New Projects

**Before (v1.0):**
```bash
recall newproject --create
# Then manually type in architecture, state, decisions...
# Takes 10 minutes to set up properly
```

**After (v2.0):**
```bash
recall newproject --create --template api-server
# Everything pre-configured with best practices!
# Takes 10 seconds
```

---

### Performance

**Before (v1.0):**
```bash
recall myproject  # 50ms every time (reads from disk)
recall myproject  # 50ms
recall myproject  # 50ms
```

**After (v2.0):**
```bash
recall myproject  # 50ms first time (reads from disk + caches)
recall myproject  # 5ms from cache ⚡
recall myproject  # 5ms from cache ⚡
```

## 💡 Tips

- Use `--search` when you have many projects
- Tag your projects by type, technology, or client for easy filtering
- Use templates when creating new projects to save setup time
- Run `--analyze` after major dependency changes
- Install git hooks (`--install-hook`) for automatic updates on every commit
- Run `--git-log` daily or weekly if not using git hooks
- Use `--insights` to see patterns across all your projects
- Export backups periodically (`--export`) for data safety
- Check logs at `~/.local/share/recall/logs/recall.log` if something goes wrong
- The readiness report tells you exactly what to fix before coding

## 📝 Dependencies

**Core System:** Pure Python standard library only - no external packages needed!

**Optional Enhancements:**
- `rich>=13.0.0` - Beautiful terminal UI (graceful fallback without it)

**Development (if contributing):**
```bash
pip install -r requirements-dev.txt
# Includes: pytest, pytest-cov, mypy, black, flake8
```

---

## 📊 Project Status

Recall is a personal tool I built and actively use in my daily development workflow. I'm sharing it publicly in case others find it useful for solving the same context loss problems with AI coding assistants.

**What to Expect:**
- ✅ Stable and production-ready (I use it every day)
- ✅ Well-documented and tested
- ✅ Zero dependencies = easy to install and maintain
- 💡 Maintained on a best-effort basis
- 🤝 PRs and contributions welcome!

**Community:**
- 🐛 [Report bugs or request features](https://github.com/seheart/recall/issues)
- 💬 [Discussions and questions](https://github.com/seheart/recall/discussions)
- ⭐ Star the repo if you find it useful!

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

Built with ❤️ by [ANT](https://ant312.com)

---

**Result:** Claude Code becomes your fully project-aware development partner! 🚀
