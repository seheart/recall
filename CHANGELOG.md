# Changelog

All notable changes to Recall will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.6.2] - 2025-10-22

**Initial versioned release** - Establishing baseline for semantic versioning

### ✨ Added

**Core Features:**
- Project memory system with SQLite database
- Automatic project analysis (10+ enrichment features)
- Git integration with commit history
- Tag system for project categorization
- Auto-tagging based on tech stack detection

**Advanced Features:**
- Live Flask dashboard with WebSocket updates
- Context history tracking and rollback
- Plugin system for extensibility
- Project templates
- Import/export functionality
- Insights and analytics across projects
- Git post-commit hooks

**Enhanced Context Intelligence:**
- 🔥 Hot files tracking (most modified files)
- 🎯 Entry points detection (main files, CLI, API)
- ⚙️ Common workflows extraction (run, test, build commands)
- 📝 Working tree state capture (uncommitted changes)
- 🎨 Architecture patterns detection
- 🔌 External integrations detection (APIs, services)
- 🔗 File relationships analysis (coupled files)
- 🐛 Known issues tracking (FIXMEs, bugs)
- 📊 Project health metrics (CI/CD, testing, linting)

**User Experience:**
- Beautiful Rich-formatted terminal output
- Auto-refresh on project load (if data > 1 day old)
- Claude-specific instructions on every recall
- Comprehensive help and examples

**Developer Tools:**
- Database migrations system
- Configuration management
- Access verification for development tools
- Fuzzy project name matching

### 🔨 Infrastructure

- Automated versioning system (this release!)
- VERSION file and __version__.py
- bump_version.py script for version management
- generate_changelog.py for automated changelog generation
- `recall --version` command

### 📚 Documentation

- Comprehensive README with examples
- Session finalization best practices guide
- Style guide for UI components
- Inline help for all commands

### 🎯 Path to v1.0

**Next milestones:**
- v0.7.0: Testing suite (80%+ coverage) + comprehensive docs
- v0.8.0: Security audit + performance optimization
- v0.9.0: Public beta testing
- v1.0.0: Production-ready release

---

## Links

- [Repository](https://github.com/seheart/recall)
- [Issues](https://github.com/seheart/recall/issues)
