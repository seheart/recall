# Recall Usage Guide

## 💻 Platform Support

**Supported Platforms:**
- 🐧 **Linux** - Fully supported and tested
- 🍎 **macOS** - Fully supported (requires Python 3.8+)
- ❌ **Windows** - Not supported

**Requirements:**
- Python 3.8+
- Git (for git integration features)

## 🚀 Getting Started

### 1. Setup
```bash
cd /home/seth/Projects/recall
python3 setup.py
```

### 2. Create Your First Project
```bash
recall my-api --create
```

Follow the interactive prompts to set up your project context.

### 3. Load Project Context
```bash
recall my-api
```

This loads complete project context that you can then provide to Claude Code.

## 📋 Command Reference

| Command | Description | Example |
|---------|-------------|---------|
| `recall project-name` | Load project context | `recall my-api` |
| `recall project-name --create` | Create new project | `recall new-app --create` |
| `recall --list` | List all projects | `recall --list` |
| `recall project --status` | Show project status | `recall my-api --status` |
| `recall` (in project dir) | Auto-detect and load | `cd ~/Projects/my-app && recall` |

## 🎯 Workflow Example

### Starting a New Project
```bash
# Create project
recall blog-api --create

# Follow prompts:
# - Description: Personal blog API server
# - Directory: /home/seth/Projects/blog-api
# - Tech stack: Node.js + Express + MongoDB
# - Language: JavaScript
# - Framework: Express.js
# - Status: Planning
```

### Continuing Work on Existing Project
```bash
# Load project context
recall blog-api

# Output shows:
# - Architecture decisions
# - Current status
# - Recent work done
# - Next steps planned

# Now use this context with Claude Code for development
```

### Updating Project Progress
```python
# In your Python scripts or when needed
from project_memory import ProjectMemory

memory = ProjectMemory()

# Log what you accomplished
memory.log_session(
    "blog-api",
    summary="Implemented user authentication",
    accomplishments=[
        "Created user registration endpoint",
        "Added JWT token generation",
        "Implemented login/logout functionality"
    ],
    decisions=[
        "Chose bcrypt for password hashing",
        "Set JWT expiry to 24 hours"
    ],
    next_steps=[
        "Add password reset functionality",
        "Implement user profile endpoints",
        "Add input validation"
    ],
    files_changed=[
        "routes/auth.js",
        "middleware/auth.js",
        "models/User.js"
    ]
)

# Record important decisions
memory.record_decision(
    "blog-api",
    "authentication_method",
    "JWT tokens",
    "Chosen for stateless authentication, easier to scale"
)
```

## 🧠 Integration with Claude Code

When you run `recall project-name`, you get formatted context like this:

```
PROJECT MEMORY LOADED: BLOG-API

📁 PROJECT INFO:
• Name: blog-api
• Description: Personal blog API server
• Directory: /home/seth/Projects/blog-api
• Last Updated: 2024-09-25 11:45:23

🏗️ ARCHITECTURE:
• stack: Node.js + Express + MongoDB
• language: JavaScript
• framework: Express.js
• database: MongoDB with Mongoose ODM

⚡ CURRENT STATE:
• current_feature: User authentication
• status: In development

🎯 KEY DECISIONS:
• authentication_method: JWT tokens
  └─ Reasoning: Stateless auth, easier to scale
• password_hashing: bcrypt
  └─ Reasoning: Industry standard, secure

📝 RECENT WORK:
Session 1 (2024-09-25):
• Summary: Implemented user authentication
• Done:
  • Created user registration endpoint
  • Added JWT token generation
  • Implemented login/logout functionality
• Next:
  • Add password reset functionality
  • Implement user profile endpoints
  • Add input validation

💡 You now have complete context for this project.
Continue development with full awareness of architecture, decisions, and progress.
```

**Copy this entire context** and provide it to Claude Code when you start working on the project. Claude Code will then have complete project awareness!

## 🔄 Typical Development Workflow

### Day 1: Starting New Project
```bash
# Create and set up project
recall ecommerce-site --create

# Work with Claude Code using the loaded context
# Build initial architecture, make decisions
```

### Day 2: Continue Development
```bash
# Load yesterday's context
recall ecommerce-site

# Copy context to Claude Code
# Continue where you left off with full awareness
```

### Day 3: Major Progress
```bash
# Load context
recall ecommerce-site

# After significant work, update progress (optional - can be automated)
# Log what was accomplished, decisions made, next steps
```

### Weeks Later: Return to Project
```bash
# Instantly remember everything
recall ecommerce-site

# Claude Code gets complete project history
# No need to re-explain architecture or decisions
```

## 💡 Tips

1. **Auto-detection**: Run `recall` in project directories for automatic detection
2. **Regular updates**: Log major sessions to keep context current
3. **Decision tracking**: Record why you made architectural choices
4. **Directory linking**: Set project directory for easier management
5. **Status updates**: Keep current status field updated for quick context

## 🚀 Advanced Features

### Project Templates
Create templates for common project types by exporting/importing context.

### Git Integration
Recall can detect git repositories and incorporate commit history.

### Team Sharing
Export project contexts to share with team members.

---

**Result: Claude Code becomes your project-aware development partner!** 🎯