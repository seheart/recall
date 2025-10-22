# Recall Dashboard Tooltip Fixes and Platform Documentation

Session Date: October 22, 2025

## Overview

Fixed tooltip positioning issues on the Insights page dashboard and added comprehensive platform support documentation across all user-facing documentation.

## Dashboard UX Improvements

### Tooltip Positioning Fixes

**Problem**: User reported tooltips were going off-screen and were difficult to read.

**Solutions Implemented**:

1. **ApexCharts Tooltips** (templates/dashboard.html):
   - Changed from fixed `topRight` position to `followCursor: true`
   - Tooltips now follow mouse cursor for better readability
   - Added custom tooltip formatters to all 6 charts for concise display
   - Added CSS constraints: max-width 200px, text-overflow ellipsis

2. **Top-Level Stat Card Tooltips**:
   - Changed from appearing above cards (`bottom: 100%`) to below (`top: 100%`)
   - Prevents tooltips from going off-screen at the top of viewport
   - Updated arrow pointer direction (now points upward)

3. **Removed Redundant Tooltips**:
   - Removed tooltips from individual project card stats (Sessions, Context, Tags)
   - Top-level cards already have comprehensive tooltips explaining these metrics

**Chart Tooltip Updates**:
- Activity Donut: "X projects"
- Health Gauge: "X%"
- Tech Stack: Shows value only
- Architecture Pie: Shows count
- Integrations Pie: Shows count
- Most Active Bar: "X sessions"

## Documentation Updates

### Platform Support Documentation

Added clear platform compatibility information to all documentation:

**Supported Platforms**:
- 🐧 Linux - Fully supported and tested
- 🍎 macOS - Fully supported (Python 3.8+)
- ❌ Windows - Not supported

**Files Updated**:

1. **README.md**:
   - Added platform badge in header
   - New "System Requirements" section with installation instructions
   - macOS installation via Homebrew
   - Linux installation via apt/dnf/pacman
   - Dependency installation commands

2. **templates/dashboard.html** (About page):
   - Added "System Requirements" section
   - Lists supported platforms and dependencies
   - Visible in dashboard About tab

3. **USAGE.md**:
   - Added "Platform Support" section at top
   - Clear requirements list

**Dependencies Documented**:
- Python 3.8+ (required)
- Git (required for git features)
- Flask, Flask-SocketIO (for dashboard)
- Rich (optional, for terminal UI)

## Technical Details

### CSS Changes
```css
.apexcharts-tooltip {
    max-width: 200px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

.tooltip:hover::after {
    top: 100%;  /* Changed from bottom: 100% */
    margin-top: 4px;  /* Changed from margin-bottom */
}

.tooltip:hover::before {
    border-bottom-color: var(--border);  /* Arrow now points up */
}
```

### JavaScript Changes
```javascript
// Global tooltip config
tooltip: {
    followCursor: true,  // Changed from fixed position
    theme: 'dark',
    style: { fontSize: '12px' }
}

// Per-chart formatters
tooltip: {
    y: {
        formatter: (val) => `${val} projects`  // Concise format
    }
}
```

## Files Modified

1. `templates/dashboard.html` (3 changes):
   - CSS tooltip positioning (lines 683-713)
   - ApexCharts global config (line 2543)
   - About page content (lines 3055-3068)
   - Removed project card tooltips (lines 1903-1913)

2. `README.md` (2 additions):
   - Platform badge (line 9)
   - System Requirements section (lines 150-187)

3. `USAGE.md` (1 addition):
   - Platform Support section (lines 3-12)

## User Feedback

User responses during implementation:
- "wow they look great!" (initial charts)
- "gorgeous! love it" (after border removal)
- Clean tooltip positioning approved

## Testing Notes

- All tooltips tested in dashboard
- Tooltips stay visible and readable
- No off-screen rendering issues
- Platform documentation reviewed across all files
- Installation instructions verified for accuracy

## Commits

- Commit 1: feat: Add spectacular ApexCharts visualizations to Insights page
- Commit 2 (pending): fix: Improve tooltip positioning and add platform docs
