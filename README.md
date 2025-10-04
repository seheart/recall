# Recall - Project Memory System for Claude Code

Give Claude Code perfect project memory so it can work as your development partner across sessions without losing context.

## 🎯 What It Does

- **Remembers Everything** - Architecture, decisions, progress, dependencies, tests, deployment
- **Auto-Analyzes Projects** - Detects tech stack, frameworks, Docker, databases, CI/CD automatically
- **Tracks Progress** - Auto-logs sessions from git commits
- **Development Readiness** - Reports what's working and what needs attention
- **Manages Issues** - Track bugs, blockers, documentation, conventions
- **Instant Context** - Load complete project awareness in one command

## 🚀 Quick Start

### Installation
```bash
cd /home/seth/Projects/recall
chmod +x recall.py

# Optional: Add to PATH for global access
ln -s $(pwd)/recall.py ~/bin/recall
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
recall --list                 # List all projects
```

### Advanced Commands
```bash
recall project --git-log --days 30    # Auto-log from last 30 days
recall project --status               # Show detailed project status
recall project --no-verify            # Skip environment verification
recall --verify-only                  # Only check dev environment
```

### Helper Commands
```bash
# Track issues and blockers
python3 helpers.py add-issue project "bug_key" "Description"
python3 helpers.py add-blocker project "blocker_key" "Description"
python3 helpers.py remove-issue project "bug_key"

# Add documentation and integrations
python3 helpers.py add-doc project "API Docs" "https://docs.example.com"
python3 helpers.py add-integration project "Stripe" "Payment processing"

# Track code conventions
python3 helpers.py add-convention project "naming" "Use PascalCase for components"
```

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
cd ~/Projects/my-awesome-app

# 1. Create project
recall my-awesome-app --create --non-interactive

# 2. Auto-populate everything
recall my-awesome-app --analyze

# 3. Auto-log git history
recall my-awesome-app --git-log --days 90

# 4. Add custom context
python3 helpers.py add-doc my-awesome-app "Figma" "https://figma.com/file/abc"
python3 helpers.py add-integration my-awesome-app "Stripe" "Uses Stripe.js v3"
python3 helpers.py add-convention my-awesome-app "testing" "All components need tests"
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

# Next session: Update recall with new commits
recall my-awesome-app --git-log

# Sessions automatically created from commits! 🎉
```

### Managing Issues
```bash
# Found a bug? Track it
python3 helpers.py add-issue my-awesome-app "login_safari" "Login broken on Safari 15+"

# Blocked? Track that too
python3 helpers.py add-blocker my-awesome-app "api_key" "Need production API key from client"

# When resolved
python3 helpers.py remove-issue my-awesome-app "login_safari"
python3 helpers.py remove-blocker my-awesome-app "api_key"
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

```
/home/seth/Projects/recall/
├── recall.py              # Main command script
├── project_memory.py      # Core memory system
├── database.py           # SQLite database management
├── access_verifier.py    # GitHub/server/system access verification
├── auto_analyzer.py      # Auto-detect project details
├── status_reporter.py    # Development readiness reports
├── git_logger.py         # Auto-log sessions from git
├── helpers.py            # Issue/doc/convention helpers
├── projects.db          # SQLite database (auto-created)
├── docs/                # Documentation
├── requirements.txt     # Dependencies (none needed!)
├── README.md           # This file
└── ENHANCEMENTS.md     # Detailed enhancement docs
```

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
from project_memory import ProjectMemory

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

## 🆕 What's New

This system now includes:

- **🔍 Auto-Analyzer** - Detects Python, Docker, databases, tests, CI/CD, environment
- **📊 Readiness Reports** - Know exactly what's ready and what's not
- **🔄 Git Auto-Logging** - Sessions created automatically from commits
- **🐛 Issue Tracking** - Track bugs, blockers with helper commands
- **📚 Documentation Links** - Store links to Figma, wikis, API docs
- **🔌 Integration Tracking** - Remember third-party service details
- **📐 Convention Tracking** - Document code patterns and standards
- **✅ Comprehensive Checks** - Verify dependencies, environment, git status

See [ENHANCEMENTS.md](ENHANCEMENTS.md) for complete details.

## 💡 Tips

- Run `--analyze` after major dependency changes
- Run `--git-log` daily or weekly to keep sessions current
- Use helpers to track issues as you discover them
- Add documentation links to keep everything in one place
- The readiness report tells you exactly what to fix before coding

## 📝 Zero Dependencies

Pure Python standard library only - no external packages needed!

---

**Result:** Claude Code becomes your fully project-aware development partner! 🚀

For questions or issues: https://github.com/anthropics/claude-code/issues
