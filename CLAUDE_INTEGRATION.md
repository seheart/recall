# Claude Code Integration Guide

## 🎯 Goal
Automatically load project context into Claude Code memory without manual copy/paste.

## 🚀 Quick Start

### Method 1: The `--claude` Flag (RECOMMENDED)
```bash
recall ant312 --claude
```

**What happens:**
1. ✅ Loads full project context
2. ✅ Generates readiness report
3. ✅ Saves context to `~/.claude/recall_ant312.txt`
4. ✅ **Copies context to clipboard automatically**
5. ✅ Launches Claude Code
6. ✅ **Just paste (Ctrl+Shift+V) in Claude and you're ready!**

### Method 2: Standalone Script
```bash
recall-claude ant312
```

Same as Method 1, but as a separate command.

## 📋 Complete Workflow

### Initial Project Setup
```bash
cd ~/Projects/my-awesome-app

# 1. Create and populate recall
recall my-awesome-app --create --non-interactive
recall my-awesome-app --analyze
recall my-awesome-app --git-log --days 90

# 2. Launch Claude Code with context
recall my-awesome-app --claude

# 3. In Claude Code: Paste (Ctrl+Shift+V)
# Context is automatically in clipboard!
```

### Daily Development
```bash
# Update git sessions
recall my-awesome-app --git-log

# Launch Claude Code with updated context
recall my-awesome-app --claude

# Paste in Claude Code → Full context loaded!
```

## 🔧 How It Works

### When you run `recall project --claude`:

1. **Context Generation**
   - Loads project from recall database
   - Formats PROJECT MEMORY section
   - Adds comprehensive readiness report
   - Saves to `~/.claude/recall_project.txt`

2. **Clipboard Integration**
   - Automatically copies full context using `wl-copy`
   - Works on Wayland (Hyprland, Sway, etc.)
   - Falls back gracefully if clipboard unavailable

3. **Claude Code Launch**
   - Executes `claude` command
   - Context is ready in clipboard
   - Just paste and start working!

## 📂 Context File Location

Context is saved to:
```
~/.claude/recall_<project-name>.txt
```

You can always manually load it:
```bash
cat ~/.claude/recall_ant312.txt
```

Or manually copy to clipboard:
```bash
cat ~/.claude/recall_ant312.txt | wl-copy
```

## 🎨 What Gets Pasted

When you paste in Claude Code, you provide:

```
PROJECT MEMORY LOADED: MY-PROJECT

📁 PROJECT INFO:
• Name, description, directory, last updated

🏗️ ARCHITECTURE:
• Tech stack, frameworks, versions

⚡ CURRENT STATE:
• Status, current focus, recent work

🎯 KEY DECISIONS:
• Important decisions with reasoning

⚙️ ENVIRONMENT:
• How to run, build, test, deploy

📝 RECENT WORK:
• Auto-logged git sessions
• Recent accomplishments
• Next steps

======================================================================
🔍 DEVELOPMENT READINESS REPORT: MY-PROJECT
======================================================================

📋 SYSTEM CHECKS:
  ✅ All working components

⚠️  WARNINGS:
  ⚠️  Things needing attention

💡 INFORMATION:
  ℹ️  Additional context

======================================================================
✅ ALL SYSTEMS GO - Ready for development!
======================================================================
```

## 💡 Tips

### Keep Context Updated
```bash
# Before each session
recall my-project --git-log    # Update from git
recall my-project --claude     # Launch with fresh context
```

### Quick Re-paste
If you need to re-provide context mid-session:
```bash
# In terminal:
cat ~/.claude/recall_my-project.txt | wl-copy

# In Claude Code:
Ctrl+Shift+V (paste)
```

### Multiple Projects
Switch between projects easily:
```bash
recall ant312 --claude         # Start working on ant312
# Close Claude, then:
recall other-project --claude  # Switch to other-project
```

## 🔍 Alternative: Manual Workflow

If you prefer manual control:

```bash
# 1. Load context (just display)
recall ant312

# 2. Copy the PROJECT MEMORY section manually
# 3. Run cdev
cdev

# 4. Paste into Claude Code
```

## ⚡ Power User Workflow

```bash
# Complete setup in one go
recall my-app --create --non-interactive && \
recall my-app --analyze && \
recall my-app --git-log --days 90 && \
recall my-app --claude

# Then paste in Claude → Ready to code!
```

## 🐛 Troubleshooting

### Context not in clipboard?
```bash
# Manually copy:
cat ~/.claude/recall_project.txt | wl-copy
```

### Can't find claude command?
Make sure Claude Code is installed and `claude` is in PATH.

### Clipboard not working?
Install `wl-clipboard`:
```bash
sudo pacman -S wl-clipboard
```

## 📝 Summary

**Before (Manual):**
1. Run `recall project`
2. Scroll up to find PROJECT MEMORY section
3. Manually select and copy
4. Run `cdev`
5. Paste in Claude Code

**After (Automatic):**
1. Run `recall project --claude`
2. Paste in Claude Code (already in clipboard!)
3. Done! 🎉

---

**Result:** One command to load context + launch Claude Code with project memory ready!
