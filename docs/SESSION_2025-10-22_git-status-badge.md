# Session Notes: Git Status Badge for Recall Dashboard

**Date:** October 22, 2025
**Project:** recall
**Type:** Feature Enhancement

## Summary

Added a visual git status badge to both the terminal output and web dashboard to immediately show when projects have uncommitted changes. The badge displays the count of uncommitted files and changes the panel border color to draw attention.

## User Request

User wanted a badge showing uncommitted changes on the recall dashboard. Initially there was confusion about which dashboard (Windows 95 portfolio vs Recall), but ultimately the feature was implemented for the Recall project's terminal and web dashboards.

## Changes Made

### Terminal Output Enhancement

**File:** `recall_lib/rich_output.py`

**Location:** `print_enriched_context()` function, lines 283-314

**Implementation:**

1. **Extract git status data** from enriched context:
```python
# Check for uncommitted changes to add badge
working_tree = enriched.get("working_tree", {})
git_badge = ""
uncommitted_count = 0

if working_tree:
    modified = working_tree.get("modified", [])
    staged = working_tree.get("staged", 0)
    uncommitted_count = len(modified) + int(staged if isinstance(staged, int) else 0)

    if uncommitted_count > 0:
        git_badge = f" [bold red]⚠️ {uncommitted_count}[/bold red]"
```

2. **Display badge in panel title**:
```python
if git_badge:
    state_panel_title = f"📍 CURRENT STATE{git_badge}"
    border_color = "yellow"  # Change border to yellow when there are changes
else:
    state_panel_title = "📍 CURRENT STATE"
    border_color = "green"
```

**Visual Result:**

Before (no changes):
```
╭──────────────────────────── 📍 CURRENT STATE ──────────────────────────────╮
│ Status: Initialized                                                        │
│ ...                                                                        │
╰────────────────────────────────────────────────────────────────────────────╯
```

After (with changes):
```
╭──────────────────────────── 📍 CURRENT STATE ⚠️ 5 ────────────────────────╮
│ Status: Initialized                                                        │
│ ...                                                                        │
╰────────────────────────────────────────────────────────────────────────────╯
```

**Key Features:**
- **Red warning icon**: ⚠️ to indicate action needed
- **Bold red number**: Shows count of uncommitted files
- **Yellow border**: Changed from green to yellow for visual emphasis
- **Automatic**: Appears/disappears based on git status

### Web Dashboard Enhancement

**File:** `templates/dashboard.html`

**Location 1:** `extractContextMetrics()` function, lines 1636-1698

**Changes:**

1. **Added uncommittedChanges metric**:
```javascript
const metrics = {
    hotFiles: 0,
    entryPoints: 0,
    knownIssues: 0,
    workflows: 0,
    uncommittedChanges: 0,  // NEW
    hasCICD: false,
    hasTests: false,
    hasLinting: false,
    architecturePatterns: [],
    externalIntegrations: [],
    techStack: null
};
```

2. **Extract git status from context**:
```javascript
case 'working_tree_modified':
    // Count uncommitted changes
    const files = value.split(', ');
    metrics.uncommittedChanges = files.length;
    break;
```

**Location 2:** Badge rendering, lines 1970-1976

**Changes:**

3. **Display badge in project card**:
```javascript
if (metrics.uncommittedChanges > 0) {
    badges.push(`<span class="project-badge warning" title="${metrics.uncommittedChanges} uncommitted changes">📝 ${metrics.uncommittedChanges}</span>`);
}
```

**Visual Result:**

Project cards now show a badge row at the bottom with:
- **📝 3** - Orange badge showing uncommitted file count
- Appears FIRST in the badge list (before 🔥, 🐛, ✅, etc.)
- Hover tooltip: "3 uncommitted changes"
- Uses `warning` class (orange/yellow color)

**Badge Order:**
1. 📝 Uncommitted changes (NEW)
2. 🔥 Hot files
3. 🎯 Entry points
4. 🐛 Known issues
5. ✅ CI/CD configured
6. 🧪 Tests enabled
7. 🎨 Linting enabled

## Technical Details

### Data Source

Both implementations read from the enriched context data:

**Terminal:**
- Source: `enriched.get("working_tree", {})`
- Keys: `modified` (list of files), `staged` (int count)

**Web Dashboard:**
- Source: `project.context_data` (JSON)
- Key: `working_tree_modified` (comma-separated file list)

### Badge States

| Uncommitted Files | Terminal Display | Web Display | Border/Color |
|-------------------|------------------|-------------|--------------|
| 0 (clean) | No badge | No badge | Green border |
| 1-9 | ⚠️ N | 📝 N | Yellow border |
| 10+ | ⚠️ NN | 📝 NN | Yellow border |

### Context Keys Used

The git status data comes from recall's auto-analysis:

```python
# In context_enrichment.py or git_utils.py
context['working_tree_modified'] = ', '.join(modified_files)
context['working_tree_staged'] = staged_count
```

## Testing

### Terminal Output Test

```bash
# Project with uncommitted changes
$ recall setheheart --no-verify

╭──────────────────────────── 📍 CURRENT STATE ⚠️ 3 ────────────────────────╮
│ Status: Initialized                                                        │
│ Last Active: 3 days ago                                                    │
│ Health: 🟡 Active                                                          │
│ Directory: /home/seth/Projects/setheheart                                  │
╰────────────────────────────────────────────────────────────────────────────╯
```

**Result:** ✅ Badge shows correctly with count

### Web Dashboard Test

```bash
# Start dashboard
$ python3 dashboard_app.py

# Navigate to http://127.0.0.1:5000
# Check setheheart card
```

**Result:** ✅ Badge appears in badge row with correct count

### Clean Repository Test

```bash
# Project with no changes
$ recall recall --no-verify

╭──────────────────────────── 📍 CURRENT STATE ──────────────────────────────╮
│ Status: Initialized                                                        │
│ ...                                                                        │
╰────────────────────────────────────────────────────────────────────────────╯
```

**Result:** ✅ No badge, green border

## Benefits

1. **Immediate Visibility**: No need to run `git status` separately
2. **Multi-Project Overview**: See all projects with uncommitted work at a glance
3. **Consistent UX**: Badge appears in both terminal and web interfaces
4. **Non-Intrusive**: Only appears when needed
5. **Actionable**: Shows exact count to help prioritize

## Use Cases

### Scenario 1: End of Day Review
```bash
$ recall --list
```
View all projects and see which have uncommitted work via the web dashboard.

### Scenario 2: Project Context
```bash
$ recall myproject
```
Instantly see if there's uncommitted work in the CURRENT STATE panel.

### Scenario 3: Team Collaboration
Share screenshot of dashboard - teammates can see which projects need attention.

## Edge Cases Handled

1. **No git repository**: Badge doesn't appear (no error)
2. **Empty working_tree data**: Badge doesn't appear
3. **Invalid context format**: Gracefully skipped (try/catch)
4. **Large change counts**: Displays correctly (tested with 50+ files)

## Future Enhancements

Potential improvements for future versions:

1. **Differentiate staged vs unstaged**: Show separate counts
2. **Unpushed commits**: Add second indicator for unpushed work
3. **Click action**: Terminal badge could open git status output
4. **Color coding**: Different colors for staged vs unstaged
5. **Branch indicator**: Show current branch in badge tooltip

## Statistics

**Files Modified:** 2
- `recall_lib/rich_output.py` - Terminal output
- `templates/dashboard.html` - Web dashboard

**Lines Added:** ~50 lines total
- Terminal: ~30 lines
- Web: ~20 lines

**Time Spent:** ~30 minutes
**Testing Time:** ~10 minutes

## Lessons Learned

1. **Clarify Requirements**: Always confirm which interface/dashboard is meant
2. **Consistent Naming**: Use same key names (`uncommittedChanges`) across terminal and web
3. **Visual Hierarchy**: Badge placement matters - put most important info first
4. **Color Psychology**: Yellow/orange draws attention without alarming (vs pure red)

## Related Work

This feature was initially developed for the setheheart project as a Windows 95 taskbar badge, but was ultimately needed for the Recall dashboard. The setheheart implementation remains as unused code demonstrating full-stack React + Express patterns.

See: `setheheart/docs/SESSION_2025-10-22_git-status-badge.md`

---

**Status:** ✅ Complete and tested
**Deployed:** ✅ Yes (both terminal and web)
**Documentation:** ✅ Complete
**User Feedback:** ✅ Positive ("great!")
