# Recall - Project Memory System for Claude Code

## 🎯 Mission
Give Claude Code perfect project memory so it can work as your development partner across sessions without losing context.

## 🧠 Core Concept
Instead of rebuilding Claude Code, we add a simple memory layer that loads project context when needed.

```
You → recall api-server → Claude Code (with full project context)
```

## 🏗️ Architecture

### Components
1. **`recall` Command** - Entry point script
2. **ProjectMemory Class** - Core memory system
3. **SQLite Database** - Persistent storage
4. **Context Loader** - Formats data for Claude Code

### Data Flow
```
User runs: recall project-name
↓
Load project context from database
↓
Format context for Claude Code system prompt
↓
Start Claude Code session with full project awareness
```

## 📊 What Gets Stored

| Category | Purpose | Example |
|----------|---------|---------|
| **Project State** | Current status and focus | "Implementing JWT auth, login component done" |
| **Architecture** | Tech stack and structure | "React + Node.js + PostgreSQL, microservices" |
| **Recent Changes** | Last session's work | "Fixed API rate limiting, added user validation" |
| **Decisions Made** | Why choices were made | "Chose Prisma over raw SQL for type safety" |
| **Environment** | Setup and deployment | "Docker containers, deployed on AWS ECS" |
| **Next Steps** | Planned work | "Add password reset, implement user roles" |
| **File Structure** | Key files and locations | "/src/auth/, /api/users/, /tests/integration/" |
| **Dependencies** | Libraries and versions | "express@4.18.2, jwt@9.0.0, bcrypt@5.1.0" |

## 🚀 Usage Workflows

### Starting Work on Existing Project
```bash
recall api-server
```
**Result:** Claude Code instantly knows:
- What we're building (Node.js API server)
- Current progress (JWT auth in progress)
- Architecture decisions (Express + PostgreSQL)
- Next steps (password reset feature)
- File structure and key components

### Creating New Project
```bash
recall new-project --create
```
**Result:**
- Creates new project entry in database
- Prompts for initial architecture details
- Sets up tracking for future sessions

### Viewing Project Status
```bash
recall --list              # Show all projects
recall api-server --status # Show specific project state
recall --recent            # Show recently worked projects
```

## 💾 Database Schema

```sql
-- Projects table
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Project context (key-value storage)
CREATE TABLE project_context (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    category TEXT,  -- 'architecture', 'state', 'decisions', etc.
    key TEXT,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id)
);

-- Session history
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    summary TEXT,
    accomplishments TEXT,
    decisions_made TEXT,
    next_steps TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id)
);
```

## 📁 File Structure
```
/home/seth/Projects/recall/
├── docs/                     # This Obsidian vault
│   ├── .obsidian/           # Obsidian configuration
│   └── overview.md          # This file
├── recall.py                # Main command script
├── project_memory.py        # Core memory system
├── context_formatter.py     # Formats data for Claude Code
├── projects.db             # SQLite database
├── requirements.txt        # Python dependencies
└── README.md              # Setup instructions
```

## 🔄 Implementation Phases

### Phase 1: Core System
- [x] Create project structure and Obsidian vault
- [ ] Build SQLite database schema
- [ ] Implement ProjectMemory class
- [ ] Create basic recall command
- [ ] Test with sample project

### Phase 2: Context Integration
- [ ] Build context formatter for Claude Code
- [ ] Implement automatic session updates
- [ ] Add project discovery (detect from directory)
- [ ] Create project templates

### Phase 3: Advanced Features
- [ ] Project relationships and dependencies
- [ ] Code pattern learning
- [ ] Automatic architecture detection
- [ ] Integration with git history

## 🎯 Success Criteria

### Must Have
- ✅ Load complete project context in < 2 seconds
- ✅ Remember architecture decisions and reasoning
- ✅ Track progress between sessions
- ✅ Simple command-line interface

### Should Have
- Auto-detect project from current directory
- Git integration for change tracking
- Export/import project contexts
- Multiple project templates

### Could Have
- Web dashboard for project overview
- Integration with other development tools
- Team sharing capabilities
- Advanced analytics

## 🚦 Getting Started

### Installation
```bash
cd /home/seth/Projects/recall
pip install -r requirements.txt
./setup.py install
```

### First Use
```bash
# Create your first project memory
recall my-api --create

# Start working with context
recall my-api
```

## 💡 Key Benefits

**For You:**
- Never lose project context again
- Pick up exactly where you left off
- Remember why decisions were made
- Track progress over time

**For Claude Code:**
- Instant project understanding
- Consistent decision-making
- Better technical advice
- Focused recommendations

---

*This system transforms Claude Code from a stateless assistant into a project-aware development partner.*