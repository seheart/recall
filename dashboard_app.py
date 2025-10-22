#!/usr/bin/env python3
"""
Recall Dashboard - Flask Web App
Serves the dashboard dynamically with fresh data on every page load
"""
from flask import Flask, render_template_string, g
from flask_socketio import SocketIO, emit
from typing import List, Dict, Any, Optional
import sqlite3
import json
import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
import threading
import time
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Restrict WebSocket CORS to localhost only for security
socketio = SocketIO(app, cors_allowed_origins=["http://127.0.0.1:5000", "http://localhost:5000"], async_mode='threading')

# Configuration constants
DB_PATH = os.path.join(os.path.expanduser('~'), '.local', 'share', 'recall', 'projects.db')
CHICAGO_TZ = ZoneInfo('America/Chicago')
AUTO_REFRESH_INTERVAL_MS = 30000  # 30 seconds
MAX_RECENT_SESSIONS = 3
DEFAULT_HOST = '127.0.0.1'  # Localhost only by default
DEFAULT_PORT = 5000
CACHE_MAX_AGE = 60  # 1 minute
MAX_RECENT_ACTIVITY_ITEMS = 20
CHANGE_POLL_INTERVAL_SECONDS = 2
ERROR_RETRY_INTERVAL_SECONDS = 5
SEARCH_DEBOUNCE_MS = 300
MAX_PROJECT_CACHE_SIZE = 50
PULSE_ANIMATION_DURATION = 2  # seconds

# Input validation
import re

def validate_project_name(name: str) -> bool:
    """Validate project name for security"""
    if not name or len(name) > 100:
        return False
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False
    return True

def get_db() -> sqlite3.Connection:
    """Get database connection from Flask g context (connection pooling)"""
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Close database connection at end of request"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def format_chicago_time(dt_string: Optional[str]) -> str:
    """Convert datetime string to Chicago time in 24-hour format"""
    if not dt_string:
        return ''
    try:
        # Parse the datetime string (it's already in localtime from the database)
        dt = datetime.fromisoformat(dt_string.replace(' ', 'T'))
        # Convert to Chicago time
        chicago_dt = dt.astimezone(CHICAGO_TZ)
        # Format as 24-hour time
        return chicago_dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, AttributeError, TypeError) as e:
        # Log the error for debugging but return original string
        logger.warning(f"Failed to parse datetime '{dt_string}': {e}")
        return dt_string

def get_projects_data() -> List[Dict[str, Any]]:
    """Get all projects with their stats"""
    try:
        db = get_db()

        cursor = db.execute('''
            SELECT
                p.id,
                p.name,
                p.description,
                p.directory,
                datetime(p.created_at, 'localtime') as created_at,
                datetime(p.updated_at, 'localtime') as updated_at,
                (SELECT COUNT(*) FROM sessions s WHERE s.project_id = p.id) as session_count,
                (SELECT COUNT(*) FROM project_context c WHERE c.project_id = p.id) as context_count,
                (SELECT GROUP_CONCAT(tag, ',') FROM project_tags t WHERE t.project_id = p.id ORDER BY tag) as tags
            FROM projects p
            ORDER BY p.name ASC
        ''')

        projects = [dict(row) for row in cursor.fetchall()]

        # Format timestamps for Chicago time
        for project in projects:
            if project.get('created_at'):
                project['created_at'] = format_chicago_time(project['created_at'])
            if project.get('updated_at'):
                project['updated_at'] = format_chicago_time(project['updated_at'])

        return projects
    except sqlite3.Error as e:
        logger.error(f"Database error in get_projects_data: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in get_projects_data: {e}")
        return []

def get_tags_data() -> List[Dict[str, Any]]:
    """Get all tags with counts"""
    try:
        db = get_db()

        cursor = db.execute('''
            SELECT
                tag,
                COUNT(*) as count
            FROM project_tags
            GROUP BY tag
            ORDER BY tag ASC
        ''')

        tags = [dict(row) for row in cursor.fetchall()]
        return tags
    except sqlite3.Error as e:
        logger.error(f"Database error in get_tags_data: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in get_tags_data: {e}")
        return []

def get_project_details() -> Dict[str, Dict[str, Any]]:
    """Get full details for all projects including context and sessions

    Optimized to avoid N+1 queries by fetching all data in 3 queries instead of 2N+1
    """
    db = get_db()

    # Query 1: Get all projects
    cursor = db.execute('SELECT id, name FROM projects')
    projects = {row['id']: row['name'] for row in cursor.fetchall()}

    # Query 2: Get ALL context items at once
    context_cursor = db.execute('''
        SELECT project_id, category, key, value
        FROM project_context
        ORDER BY project_id, category, key
    ''')

    # Group context by project_id
    all_contexts = {}
    for row in context_cursor.fetchall():
        project_id = row['project_id']
        if project_id not in all_contexts:
            all_contexts[project_id] = {}

        category = row['category']
        if category not in all_contexts[project_id]:
            all_contexts[project_id][category] = []

        all_contexts[project_id][category].append({
            'key': row['key'],
            'value': row['value']
        })

    # Query 3: Get ALL sessions at once (top 3 per project)
    # SQLite doesn't have ROW_NUMBER, so we fetch all and limit in Python
    sessions_cursor = db.execute('''
        SELECT
            project_id,
            summary,
            accomplishments,
            decisions_made,
            next_steps,
            datetime(created_at, 'localtime') as created_at
        FROM sessions
        ORDER BY project_id, created_at DESC
    ''')

    # Group sessions by project_id and take top 3
    all_sessions = {}
    for row in sessions_cursor.fetchall():
        project_id = row['project_id']
        if project_id not in all_sessions:
            all_sessions[project_id] = []

        # Only keep top N sessions per project
        if len(all_sessions[project_id]) < MAX_RECENT_SESSIONS:
            session_data = dict(row)
            # Format timestamp for Chicago time
            if session_data.get('created_at'):
                session_data['created_at'] = format_chicago_time(session_data['created_at'])
            all_sessions[project_id].append(session_data)

    # Build final details dict keyed by project name
    details = {}
    for project_id, project_name in projects.items():
        details[project_name] = {
            'context': all_contexts.get(project_id, {}),
            'sessions': all_sessions.get(project_id, [])
        }

    return details

# About page template
ABOUT_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About - Recall Dashboard</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='0.9em' font-size='90'>🧠</text></svg>">
    <style>
        body {
            font-family: "JetBrainsMono Nerd Font", "FiraCode Nerd Font", monospace;
            background: #1a1b26;
            color: #c0caf5;
            padding: 40px 20px;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
        }
        h1 { color: #7aa2f7; font-size: 32px; margin-bottom: 20px; }
        h2 { color: #7aa2f7; font-size: 24px; margin-top: 30px; margin-bottom: 15px; }
        p { margin-bottom: 15px; }
        code { background: #24283b; padding: 2px 8px; border-radius: 4px; color: #7dcfff; }
        .back-link {
            display: inline-block;
            margin-bottom: 30px;
            color: #7aa2f7;
            text-decoration: none;
            padding: 8px 16px;
            border: 1px solid #292e42;
            border-radius: 4px;
            transition: all 0.2s;
        }
        .back-link:hover { background: #24283b; }
        .feature-list { margin: 20px 0; }
        .feature-list li { margin-bottom: 10px; }
        ul { margin-left: 20px; }
    </style>
</head>
<body>
    <a href="/" class="back-link">← Back to Dashboard</a>

    <h1>🧠 About Recall</h1>

    <p>
        <strong>Recall</strong> is a project memory system designed for developers using Claude Code.
        It automatically tracks context, decisions, and development sessions across all your projects,
        giving Claude Code perfect memory of your work.
    </p>

    <h2>Key Features</h2>
    <ul class="feature-list">
        <li><strong>Automatic Context Tracking</strong> - Detects tech stack, dependencies, git status, and more</li>
        <li><strong>Session Logging</strong> - Auto-logs development sessions from git commits</li>
        <li><strong>Live Dashboard</strong> - Real-time web interface with auto-refresh</li>
        <li><strong>Cross-Project Insights</strong> - View analytics across all your projects</li>
        <li><strong>Claude Code Integration</strong> - Seamlessly works with your AI coding workflow</li>
        <li><strong>Tag System</strong> - Organize projects by technology, type, or custom labels</li>
    </ul>

    <h2>How It Works</h2>
    <p>
        Recall maintains a SQLite database at <code>~/.local/share/recall/projects.db</code> containing:
    </p>
    <ul>
        <li><strong>Projects</strong> - Each project you're tracking</li>
        <li><strong>Context</strong> - Architecture, decisions, environment details, git info, etc.</li>
        <li><strong>Sessions</strong> - Development sessions with accomplishments and next steps</li>
        <li><strong>Tags</strong> - Categorization for easy filtering</li>
    </ul>

    <h2>Technology</h2>
    <p>
        Built with Python 3, SQLite, and Flask. The dashboard uses vanilla JavaScript with
        no external dependencies for maximum performance and simplicity.
    </p>

    <h2>Open Source</h2>
    <p>
        Recall is open source and available on <a href="https://github.com/seheart/recall" target="_blank" style="color: #7aa2f7;">GitHub</a>.
        Contributions, issues, and feature requests are welcome!
    </p>

    <p style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #292e42; color: #565f89; font-size: 12px;">
        Built by <a href="https://setheheart.com" target="_blank" style="color: #7aa2f7;">Seth Eheart</a>
        of <a href="https://ant312.com" target="_blank" style="color: #7aa2f7;">ANT</a>
    </p>
</body>
</html>'''

# How to Use page template
HOW_TO_USE_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>How to Use - Recall Dashboard</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='0.9em' font-size='90'>🧠</text></svg>">
    <style>
        body {
            font-family: "JetBrainsMono Nerd Font", "FiraCode Nerd Font", monospace;
            background: #1a1b26;
            color: #c0caf5;
            padding: 40px 20px;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
        }
        h1 { color: #7aa2f7; font-size: 32px; margin-bottom: 20px; }
        h2 { color: #7aa2f7; font-size: 24px; margin-top: 30px; margin-bottom: 15px; }
        h3 { color: #7dcfff; font-size: 18px; margin-top: 20px; margin-bottom: 10px; }
        p { margin-bottom: 15px; }
        code { background: #24283b; padding: 2px 8px; border-radius: 4px; color: #7dcfff; font-size: 13px; }
        pre {
            background: #24283b;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            border: 1px solid #292e42;
        }
        pre code { padding: 0; background: none; }
        .back-link {
            display: inline-block;
            margin-bottom: 30px;
            color: #7aa2f7;
            text-decoration: none;
            padding: 8px 16px;
            border: 1px solid #292e42;
            border-radius: 4px;
            transition: all 0.2s;
        }
        .back-link:hover { background: #24283b; }
        .command { color: #9ece6a; }
        .note {
            background: #24283b;
            padding: 15px;
            border-left: 4px solid #7aa2f7;
            margin: 20px 0;
            border-radius: 4px;
        }
        ul { margin-left: 20px; }
        li { margin-bottom: 8px; }
    </style>
</head>
<body>
    <a href="/" class="back-link">← Back to Dashboard</a>

    <h1>📘 How to Use Recall</h1>

    <h2>Quick Start</h2>

    <h3>1. Create Your First Project</h3>
    <pre><code><span class="command">recall myproject --create</span></code></pre>
    <p>This creates a new project entry in the Recall database.</p>

    <h3>2. Analyze Your Project</h3>
    <pre><code><span class="command">recall myproject --analyze</span></code></pre>
    <p>Automatically detects and stores:</p>
    <ul>
        <li>Tech stack (Node.js, Python, Rust, etc.)</li>
        <li>Package manager and dependencies</li>
        <li>Git repository info and status</li>
        <li>Directory structure</li>
        <li>Environment configuration</li>
    </ul>

    <h3>3. Log Git History as Sessions</h3>
    <pre><code><span class="command">recall myproject --git-log --days 30</span></code></pre>
    <p>Imports recent git commits as development sessions, preserving your work history.</p>

    <h2>Common Commands</h2>

    <h3>View Project Status</h3>
    <pre><code><span class="command">recall myproject</span></code></pre>
    <p>Shows all stored context and recent sessions for the project.</p>

    <h3>Add Custom Context</h3>
    <pre><code><span class="command">recall myproject --add-context architecture "Microservices with Docker"</span></code></pre>
    <p>Store custom notes, decisions, or architectural details.</p>

    <h3>Add Tags</h3>
    <pre><code><span class="command">recall myproject --add-tag web --add-tag react --add-tag api</span></code></pre>
    <p>Categorize projects for easy filtering in the dashboard.</p>

    <h3>View All Projects</h3>
    <pre><code><span class="command">recall --list</span></code></pre>
    <p>List all tracked projects with their stats.</p>

    <h2>Dashboard Usage</h2>

    <h3>Start the Live Dashboard</h3>
    <pre><code><span class="command">python3 dashboard_app.py</span></code></pre>
    <p>Launches the Flask web server at <code>http://127.0.0.1:5000</code></p>

    <div class="note">
        <strong>💡 Pro Tip:</strong> The dashboard auto-refreshes every 30 seconds. Any changes you make
        via the CLI will appear automatically without manual refresh!
    </div>

    <h3>Dashboard Features</h3>
    <ul>
        <li><strong>Search</strong> - Filter projects by name, description, or tags</li>
        <li><strong>Tag Filters</strong> - Click tags to filter by technology or type</li>
        <li><strong>Sort Options</strong> - Sort by name, recent activity, sessions, or context</li>
        <li><strong>Project Details</strong> - Click any project card to view full context and sessions</li>
        <li><strong>Insights</strong> - View cross-project analytics and statistics</li>
        <li><strong>Activity Feed</strong> - See recent development sessions across all projects</li>
    </ul>

    <h3>Keyboard Shortcuts</h3>
    <ul>
        <li><code>/</code> - Focus search bar</li>
        <li><code>Esc</code> - Close modal or clear search</li>
        <li><code>r</code> - Refresh dashboard</li>
        <li><code>i</code> - Show insights</li>
        <li><code>a</code> - Show activity feed</li>
        <li><code>1/2/3</code> - Switch themes</li>
        <li><code>?</code> - Show keyboard help</li>
    </ul>

    <h2>Integration with Claude Code</h2>

    <p>When working with Claude Code, you can paste project context directly from Recall:</p>
    <ol>
        <li>Open a project in the dashboard</li>
        <li>Click "Copy to Clipboard"</li>
        <li>Paste into your Claude Code conversation</li>
    </ol>
    <p>This gives Claude perfect memory of your project's architecture, decisions, and recent work!</p>

    <div class="note">
        <strong>🚀 Next Steps:</strong> Run <code>recall --help</code> to see all available commands,
        or check out the <a href="https://github.com/seheart/recall" target="_blank" style="color: #7aa2f7;">GitHub README</a>
        for detailed documentation.
    </div>

    <p style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #292e42; color: #565f89; font-size: 12px;">
        Need help? Open an issue on <a href="https://github.com/seheart/recall/issues" target="_blank" style="color: #7aa2f7;">GitHub</a>
    </p>
</body>
</html>'''

# HTML template (same as generate_dashboard.py but with Jinja2 variables and auto-refresh)
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recall Dashboard - Project Memory System</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='0.9em' font-size='90'>🧠</text></svg>">
    <style>
        /* Theme Variables */
        :root {
            --radius: 4px;
            --shadow: none;
            --mono: "JetBrainsMono Nerd Font", "FiraCode Nerd Font", "Hack Nerd Font", ui-monospace, monospace;
            --sans: var(--mono); /* Use monospace everywhere for terminal feel */
        }

        /* Catppuccin Theme (Mocha) */
        body.theme--catppuccin {
            --bg: #1e1e2e;
            --surface: #181825;
            --surface-2: #313244;
            --text: #cdd6f4;
            --text-heading: #cdd6f4;
            --muted: #6c7086;
            --border: #45475a;
            --accent: #89b4fa;
            --accent-2: #94e2d5;
            --success: #a6e3a1;
            --error: #f38ba8;
            --warning: #f9e2af;
            --chip-bg: #11111b;
            --code-bg: #313244;
            --highlight: rgba(137, 180, 250, 0.2);
        }

        /* Catppuccin Latte Theme */
        body.theme--catppuccin-latte {
            --bg: #eff1f5;
            --surface: #e6e9ef;
            --surface-2: #ccd0da;
            --text: #4c4f69;
            --text-heading: #4c4f69;
            --muted: #6c6f85;
            --border: #acb0be;
            --accent: #1e66f5;
            --accent-2: #04a5e5;
            --success: #40a02b;
            --error: #d20f39;
            --warning: #df8e1d;
            --chip-bg: #dce0e8;
            --code-bg: #ccd0da;
            --highlight: rgba(30, 102, 245, 0.2);
        }

        /* Everforest Theme */
        body.theme--everforest {
            --bg: #2d353b;
            --surface: #343f44;
            --surface-2: #3d484d;
            --text: #d3c6aa;
            --text-heading: #d3c6aa;
            --muted: #859289;
            --border: #475258;
            --accent: #a7c080;
            --accent-2: #83c092;
            --success: #a7c080;
            --error: #e67e80;
            --warning: #dbbc7f;
            --chip-bg: #272e33;
            --code-bg: #3d484d;
            --highlight: rgba(167, 192, 128, 0.2);
        }

        /* Flexoki Light Theme */
        body.theme--flexoki-light {
            --bg: #fffcf0;
            --surface: #f2f0e5;
            --surface-2: #e6e4d9;
            --text: #100f0f;
            --text-heading: #100f0f;
            --muted: #6f6e69;
            --border: #d0cec7;
            --accent: #205ea6;
            --accent-2: #24837b;
            --success: #66800b;
            --error: #af3029;
            --warning: #bc5215;
            --chip-bg: #f2f0e5;
            --code-bg: #e6e4d9;
            --highlight: rgba(32, 94, 166, 0.2);
        }

        /* Gruvbox Theme */
        body.theme--gruvbox {
            --bg: #fbf1c7;
            --surface: #f9f5d7;
            --surface-2: #ebdbb2;
            --text: #3c3836;
            --text-heading: #282828;
            --muted: #665c54;
            --border: #d5c4a1;
            --accent: #98971a;
            --accent-2: #79740e;
            --success: #98971a;
            --error: #cc241d;
            --warning: #d65d0e;
            --chip-bg: #ebdbb2;
            --code-bg: #ebdbb2;
            --highlight: rgba(152, 151, 26, 0.2);
        }

        /* Kanagawa Theme */
        body.theme--kanagawa {
            --bg: #1f1f28;
            --surface: #16161d;
            --surface-2: #2a2a37;
            --text: #dcd7ba;
            --text-heading: #dcd7ba;
            --muted: #727169;
            --border: #363646;
            --accent: #7e9cd8;
            --accent-2: #7fb4ca;
            --success: #98bb6c;
            --error: #e82424;
            --warning: #ffa066;
            --chip-bg: #1f1f28;
            --code-bg: #2a2a37;
            --highlight: rgba(126, 156, 216, 0.2);
        }

        /* Matte Black Theme */
        body.theme--matte-black {
            --bg: #0a0a0a;
            --surface: #121212;
            --surface-2: #1e1e1e;
            --text: #e0e0e0;
            --text-heading: #ffffff;
            --muted: #888888;
            --border: #333333;
            --accent: #ffffff;
            --accent-2: #cccccc;
            --success: #00ff00;
            --error: #ff0000;
            --warning: #ffaa00;
            --chip-bg: #1a1a1a;
            --code-bg: #1e1e1e;
            --highlight: rgba(255, 255, 255, 0.1);
        }

        /* Nord Theme */
        body.theme--nord {
            --bg: #2e3440;
            --surface: #3b4252;
            --surface-2: #434c5e;
            --text: #eceff4;
            --text-heading: #eceff4;
            --muted: #d8dee9;
            --border: #4c566a;
            --accent: #88c0d0;
            --accent-2: #81a1c1;
            --success: #a3be8c;
            --error: #bf616a;
            --warning: #ebcb8b;
            --chip-bg: #2e3440;
            --code-bg: #434c5e;
            --highlight: rgba(136, 192, 208, 0.2);
        }

        /* Osaka Jade Theme */
        body.theme--osaka-jade {
            --bg: #1a2b2b;
            --surface: #1f3333;
            --surface-2: #243d3d;
            --text: #c7d6cc;
            --text-heading: #c7d6cc;
            --muted: #7a9085;
            --border: #2d4747;
            --accent: #66d9a7;
            --accent-2: #4dc98f;
            --success: #66d9a7;
            --error: #ff6b6b;
            --warning: #ffd166;
            --chip-bg: #1a2b2b;
            --code-bg: #243d3d;
            --highlight: rgba(102, 217, 167, 0.2);
        }

        /* Ristretto Theme */
        body.theme--ristretto {
            --bg: #2c2421;
            --surface: #352f2c;
            --surface-2: #403934;
            --text: #e6dcc8;
            --text-heading: #f5ede1;
            --muted: #b5a99a;
            --border: #4d4338;
            --accent: #f79a3e;
            --accent-2: #d67c2a;
            --success: #b9ca79;
            --error: #d16969;
            --warning: #e8b878;
            --chip-bg: #302a27;
            --code-bg: #403934;
            --highlight: rgba(247, 154, 62, 0.2);
        }

        /* Rose Pine Theme */
        body.theme--rose-pine {
            --bg: #191724;
            --surface: #1f1d2e;
            --surface-2: #26233a;
            --text: #e0def4;
            --text-heading: #e0def4;
            --muted: #6e6a86;
            --border: #403d52;
            --accent: #9ccfd8;
            --accent-2: #31748f;
            --success: #9ccfd8;
            --error: #eb6f92;
            --warning: #f6c177;
            --chip-bg: #1f1d2e;
            --code-bg: #26233a;
            --highlight: rgba(156, 207, 216, 0.2);
        }

        /* Tokyo Night Theme */
        body.theme--tokyo-night {
            --bg: #1a1b26;
            --surface: #16161e;
            --surface-2: #24283b;
            --text: #c0caf5;
            --text-heading: #c0caf5;
            --muted: #565f89;
            --border: #292e42;
            --accent: #7aa2f7;
            --accent-2: #7dcfff;
            --success: #9ece6a;
            --error: #f7768e;
            --warning: #e0af68;
            --chip-bg: #1f2335;
            --code-bg: #24283b;
            --highlight: rgba(122, 162, 247, 0.2);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: var(--mono);
            background: var(--bg);
            min-height: 100vh;
            padding: 12px;
            color: var(--text);
            font-size: 13px;
            line-height: 1.4;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
        }

        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            margin-bottom: 12px;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 700;
            font-size: 16px;
            color: var(--text-heading);
        }

        .theme-switch {
            display: flex;
            gap: 6px;
        }

        .theme-btn {
            padding: 10px 16px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--text);
            cursor: pointer;
            font-family: var(--mono);
            font-size: 12px;
            font-weight: normal;
            transition: all 0.15s ease;
            min-height: 44px;
            min-width: 44px;
        }

        .theme-btn:hover {
            background: var(--surface-2);
            border-color: var(--accent);
        }

        .theme-btn.active {
            background: var(--accent);
            color: var(--bg);
            border-color: var(--accent);
        }

        .theme-btn:focus-visible {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
        }

        .theme-btn:focus:not(:focus-visible) {
            outline: none;
        }

        .clear-btn {
            padding: 10px 16px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--muted);
            cursor: pointer;
            font-family: var(--mono);
            font-size: 12px;
            font-weight: normal;
            transition: all 0.15s ease;
            min-height: 44px;
            min-width: 44px;
        }

        .clear-btn:hover {
            background: var(--error, #e06c75);
            color: white;
            border-color: var(--error, #e06c75);
        }

        .clear-btn:focus-visible {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
        }

        .action-btn {
            padding: 10px 16px;
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--text);
            cursor: pointer;
            font-family: var(--mono);
            font-size: 12px;
            font-weight: 500;
            transition: all 0.15s ease;
            min-height: 44px;
            min-width: 44px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .action-btn:hover {
            background: var(--accent);
            color: var(--bg);
            border-color: var(--accent);
        }

        .action-btn:focus-visible {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
        }

        .action-btn:focus:not(:focus-visible) {
            outline: none;
        }

        header {
            background: var(--surface);
            padding: 16px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            margin-bottom: 12px;
        }

        h1 {
            font-size: 18px;
            color: var(--text-heading);
            margin: 0 0 12px 0;
            font-weight: 600;
            letter-spacing: 0.5px;
        }

        .subtitle {
            color: var(--muted);
            font-size: 11px;
            margin-bottom: 12px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 8px;
            margin-top: 12px;
        }

        .stat-card {
            background: var(--surface-2);
            padding: 10px 12px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            text-align: center;
        }

        .stat-number {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 3px;
            color: var(--accent);
        }

        .stat-label {
            font-size: 10px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .controls {
            background: var(--surface);
            padding: 10px 12px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            margin-bottom: 12px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
        }

        .search-box {
            flex: 1;
            min-width: 200px;
        }

        .search-box input {
            width: 100%;
            padding: 6px 10px;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            font-size: 12px;
            transition: border-color 0.2s;
            background: var(--surface-2);
            color: var(--text);
            font-family: var(--mono);
        }

        .search-box input::placeholder {
            color: var(--muted);
        }

        .search-box input:focus {
            outline: none;
            border-color: var(--accent);
        }

        .tag-filters {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }

        .tag-filter {
            padding: 4px 10px;
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            cursor: pointer;
            transition: all 0.2s;
            font-size: 11px;
            color: var(--text);
        }

        .tag-filter:hover {
            background: var(--accent);
            color: var(--bg);
            border-color: var(--accent);
        }

        .tag-filter.active {
            background: var(--accent);
            color: var(--bg);
            border-color: var(--accent);
        }

        .projects-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 8px;
            margin-bottom: 12px;
        }

        .project-card {
            background: var(--surface);
            border-radius: var(--radius);
            padding: 12px;
            border: 1px solid var(--border);
            transition: all 0.2s;
            position: relative;
            cursor: pointer;
        }

        .project-card:hover {
            border-color: var(--accent);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }

        .project-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 3px;
            height: 100%;
            background: var(--accent);
        }

        .project-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 8px;
            padding-left: 8px;
        }

        .project-name {
            font-size: 13px;
            font-weight: 700;
            color: var(--text-heading);
            margin-bottom: 3px;
        }

        .project-description {
            color: var(--muted);
            margin-bottom: 8px;
            line-height: 1.5;
            font-size: 11px;
            padding-left: 8px;
        }

        .project-path {
            color: var(--muted);
            font-size: 10px;
            margin-bottom: 8px;
            word-break: break-all;
            padding-left: 8px;
        }

        .project-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-bottom: 8px;
            padding-left: 8px;
        }

        .tag {
            display: inline-block;
            padding: 2px 6px;
            background: var(--chip-bg);
            color: var(--accent);
            border-radius: var(--radius);
            font-size: 10px;
            font-weight: 500;
            border: 1px solid var(--border);
        }

        .project-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            padding-top: 8px;
            border-top: 1px solid var(--border);
            padding-left: 8px;
        }

        .project-stat {
            text-align: center;
        }

        .project-stat-number {
            font-size: 16px;
            font-weight: 700;
            color: var(--accent);
        }

        .project-stat-label {
            font-size: 9px;
            color: var(--muted);
            margin-top: 2px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .project-date {
            font-size: 10px;
            color: var(--muted);
            text-align: right;
            margin-top: 6px;
            padding-left: 8px;
        }

        .no-results {
            text-align: center;
            padding: 40px 20px;
            background: var(--surface);
            border-radius: var(--radius);
            border: 1px solid var(--border);
            color: var(--muted);
            font-size: 12px;
        }

        .no-results::before {
            content: "🔍";
            display: block;
            font-size: 32px;
            margin-bottom: 12px;
        }

        .tooltip {
            position: relative;
            cursor: help;
            border-bottom: 1px dotted var(--muted);
        }

        .tooltip:hover::after {
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: var(--surface-2);
            color: var(--text);
            padding: 8px 12px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            white-space: normal;
            max-width: 300px;
            word-wrap: break-word;
            font-size: 11px;
            z-index: 1000;
            margin-bottom: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            text-align: center;
        }

        .tooltip:hover::before {
            content: "";
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 4px solid transparent;
            border-top-color: var(--border);
            z-index: 1001;
        }

        footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--surface);
            border-top: 1px solid var(--border);
            padding: 12px 24px;
            z-index: 100;
            font-family: var(--mono);
        }

        .footer-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 100%;
            font-size: 12px;
        }

        .footer-left,
        .footer-right {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .footer-brand {
            color: var(--accent);
            font-weight: 600;
        }

        .footer-divider {
            color: var(--muted);
        }

        .footer-link {
            color: var(--accent-2);
            text-decoration: none;
            cursor: pointer;
            transition: color 0.2s;
            background: none;
            border: none;
            font-size: 12px;
            padding: 0;
            font-family: inherit;
        }

        .footer-link:hover {
            color: var(--accent);
            text-decoration: underline;
        }

        .theme-dropdown {
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--text);
            font-family: var(--mono);
            font-size: 12px;
            padding: 4px 8px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .theme-dropdown:hover {
            background: var(--surface);
            border-color: var(--accent);
        }

        .theme-dropdown:focus {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
        }

        .footer-status {
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--success);
            font-size: 11px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.5;
            }
        }

        /* Add padding to body to account for fixed footer */
        body {
            padding-bottom: 60px;
        }

        /* Tab Navigation */
        .tab-navigation {
            display: flex;
            gap: 4px;
            align-items: center;
        }

        .tab-button {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: transparent;
            border: 1px solid transparent;
            border-radius: 6px;
            color: var(--muted);
            font-family: var(--mono);
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
        }

        .tab-button:hover {
            background: var(--surface-2);
            color: var(--text);
            transform: translateY(-1px);
        }

        .tab-button:focus {
            outline: none;
            box-shadow: 0 0 0 2px var(--accent);
        }

        .tab-button.active {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }

        .tab-button.active:hover {
            background: var(--accent-2, var(--accent));
            transform: none;
        }

        .tab-icon {
            font-size: 14px;
        }

        .tab-label {
            font-weight: 600;
        }

        .tab-shortcut {
            position: absolute;
            top: 2px;
            right: 2px;
            font-size: 9px;
            padding: 1px 3px;
            background: var(--bg);
            border-radius: 2px;
            opacity: 0.5;
            line-height: 1;
        }

        .tab-button:hover .tab-shortcut {
            opacity: 0.8;
        }

        .tab-button.active .tab-shortcut {
            background: rgba(255, 255, 255, 0.2);
            opacity: 0.7;
        }

        /* Tab content areas */
        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* Content page styles */
        .content-page {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 24px;
            max-width: 900px;
            margin: 0 auto 20px;
        }

        .content-page h1 {
            color: var(--text-heading);
            font-size: 28px;
            margin-bottom: 20px;
        }

        .content-page h2 {
            color: var(--accent);
            font-size: 20px;
            margin-top: 30px;
            margin-bottom: 15px;
        }

        .content-page h3 {
            color: var(--accent-2);
            font-size: 16px;
            margin-top: 20px;
            margin-bottom: 10px;
        }

        .content-page p {
            margin-bottom: 15px;
            line-height: 1.6;
        }

        .content-page ul, .content-page ol {
            margin-left: 20px;
            margin-bottom: 15px;
        }

        .content-page li {
            margin-bottom: 8px;
        }

        .content-page code {
            background: var(--code-bg);
            padding: 2px 8px;
            border-radius: var(--radius);
            color: var(--accent-2);
            font-size: 12px;
        }

        .content-page pre {
            background: var(--surface-2);
            padding: 15px;
            border-radius: var(--radius);
            overflow-x: auto;
            border: 1px solid var(--border);
            margin: 15px 0;
        }

        .content-page pre code {
            padding: 0;
            background: none;
        }

        .note-box {
            background: var(--surface-2);
            padding: 15px;
            border-left: 4px solid var(--accent);
            margin: 20px 0;
            border-radius: var(--radius);
        }

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 2000;
            overflow-y: auto;
            padding: 20px;
        }

        .modal.active {
            display: flex;
            align-items: flex-start;
            justify-content: center;
        }

        .modal-content {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            max-width: 900px;
            width: 100%;
            margin: 40px auto;
            padding: 20px;
            position: relative;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .modal-close {
            position: absolute;
            top: 12px;
            right: 12px;
            background: var(--surface-2);
            border: 1px solid var(--border);
            color: var(--text);
            width: 32px;
            height: 32px;
            border-radius: var(--radius);
            cursor: pointer;
            font-size: 18px;
            line-height: 30px;
            text-align: center;
            transition: all 0.2s;
        }

        .modal-close:hover {
            background: var(--accent);
            color: var(--bg);
            border-color: var(--accent);
        }

        .modal-header {
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 16px;
        }

        .modal-title {
            font-size: 16px;
            font-weight: 700;
            color: var(--text-heading);
            margin-bottom: 4px;
        }

        .modal-subtitle {
            font-size: 11px;
            color: var(--muted);
        }

        .context-section {
            margin-bottom: 16px;
        }

        .context-section-title {
            font-size: 12px;
            font-weight: 700;
            color: var(--accent);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .context-items {
            background: var(--surface-2);
            padding: 10px 12px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
        }

        .context-item {
            font-size: 11px;
            padding: 4px 0;
            color: var(--text);
            border-bottom: 1px solid var(--border);
        }

        .context-item:last-child {
            border-bottom: none;
        }

        .context-key {
            color: var(--accent);
            font-weight: 600;
            margin-right: 8px;
        }

        .session-card {
            background: var(--surface-2);
            padding: 10px 12px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            margin-bottom: 8px;
        }

        .session-date {
            font-size: 10px;
            color: var(--muted);
            margin-bottom: 6px;
        }

        .session-detail {
            font-size: 11px;
            margin-bottom: 4px;
            color: var(--text);
        }

        .session-label {
            color: var(--accent);
            font-weight: 600;
        }

        .no-data {
            text-align: center;
            padding: 20px;
            color: var(--muted);
            font-size: 11px;
            font-style: italic;
        }

        @media (max-width: 768px) {
            .projects-grid {
                grid-template-columns: 1fr;
            }

            .controls {
                flex-direction: column;
                align-items: stretch;
            }

            .theme-switch {
                order: -1;
                justify-content: center;
            }

            .footer-content {
                flex-direction: column;
                gap: 8px;
                text-align: center;
            }

            .footer-left,
            .footer-right {
                flex-wrap: wrap;
                justify-content: center;
            }
        }

        /* WCAG 2.4.7: Focus indicators for keyboard navigation */
        button:focus-visible,
        a:focus-visible,
        input:focus-visible,
        .project-card:focus-visible,
        .tag-filter:focus-visible {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
        }

        /* Remove outline for mouse users */
        button:focus:not(:focus-visible),
        a:focus:not(:focus-visible) {
            outline: none;
        }

        /* High contrast mode support */
        @media (prefers-contrast: high) {
            button:focus-visible,
            a:focus-visible {
                outline-width: 3px;
            }
        }

        /* WCAG 2.3.3: Reduced motion support */
        @media (prefers-reduced-motion: reduce) {
            *,
            *::before,
            *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
                scroll-behavior: auto !important;
            }

            /* Keep essential transitions very short */
            button,
            a,
            input,
            .project-card {
                transition: background-color 0.05s ease, color 0.05s ease, border-color 0.05s ease;
            }
        }

        /* Screen reader only content - WCAG 4.1.3 */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }
    </style>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body class="theme--tokyo-night">
    <div class="container">
        <div class="topbar" role="banner">
            <div class="brand"><span style="font-size: 24px;">🧠</span> RECALL DASHBOARD</div>
            <nav class="tab-navigation" role="navigation" aria-label="Main navigation">
                <button class="tab-button active" data-tab="projects" aria-label="Projects - Press 1 for shortcut">
                    <span class="tab-icon">📁</span>
                    <span class="tab-label">Projects</span>
                    <span class="tab-shortcut">1</span>
                </button>
                <button class="tab-button" data-tab="insights" aria-label="Insights - Press 2 for shortcut">
                    <span class="tab-icon">📊</span>
                    <span class="tab-label">Insights</span>
                    <span class="tab-shortcut">2</span>
                </button>
                <button class="tab-button" data-tab="activity" aria-label="Activity - Press 3 for shortcut">
                    <span class="tab-icon">📰</span>
                    <span class="tab-label">Activity</span>
                    <span class="tab-shortcut">3</span>
                </button>
                <button class="tab-button" data-tab="how-to-use" aria-label="How to Use - Press 4 for shortcut">
                    <span class="tab-icon">📘</span>
                    <span class="tab-label">How to Use</span>
                    <span class="tab-shortcut">4</span>
                </button>
            </nav>
        </div>

        <!-- Projects Tab Content -->
        <div id="tab-projects" class="tab-content active">
            <header>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number" id="total-projects">0</div>
                        <div class="stat-label tooltip" data-tooltip="Total projects tracked in Recall. Each project maintains its own memory, context, and session history.">Projects</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="total-sessions">0</div>
                        <div class="stat-label tooltip" data-tooltip="Development sessions across all projects. Sessions are auto-logged from git commits or manually added to track work progress.">Sessions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="total-context">0</div>
                        <div class="stat-label tooltip" data-tooltip="Context items include architecture details, environment setup, decisions, git info, dependencies, and more. Auto-populated via --analyze.">Context Items</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="total-tags">0</div>
                        <div class="stat-label tooltip" data-tooltip="Unique tags used across all projects. Tags categorize projects by tech stack, type, or custom labels (e.g., web, api, python, react).">Tags</div>
                    </div>
                </div>
            </header>

            <div class="controls" role="search">
                <div class="search-box">
                    <input type="text" id="search" placeholder="🔍 Search projects..." aria-label="Search projects by name, description, or tags" />
                </div>
                <select id="sort-select" aria-label="Sort projects" style="padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--surface-2); color: var(--text); font-family: var(--mono); font-size: 12px;">
                    <option value="name-asc">Name (A-Z)</option>
                    <option value="name-desc">Name (Z-A)</option>
                    <option value="updated-desc">Recently Updated</option>
                    <option value="updated-asc">Least Recently Updated</option>
                    <option value="sessions-desc">Most Sessions</option>
                    <option value="sessions-asc">Least Sessions</option>
                    <option value="context-desc">Most Context</option>
                    <option value="context-asc">Least Context</option>
                </select>
                <button id="clear-filters" class="clear-btn" aria-label="Clear all filters and search">✕ Clear Filters</button>
                <div class="tag-filters" id="tag-filters" role="group" aria-label="Filter projects by tag"></div>
            </div>

            <div id="search-results-count" style="padding: 8px 0; color: var(--muted); font-size: 11px; text-align: center;" aria-live="polite"></div>

            <div class="projects-grid" id="projects-grid"></div>
        </div>

        <!-- Insights Tab Content -->
        <div id="tab-insights" class="tab-content">
            <div id="insights-content"></div>
        </div>

        <!-- Activity Tab Content -->
        <div id="tab-activity" class="tab-content">
            <div id="activity-content"></div>
        </div>

        <!-- How to Use Tab Content -->
        <div id="tab-how-to-use" class="tab-content">
            <div class="content-page" id="how-to-use-content"></div>
        </div>

        <!-- About Tab Content (accessible from footer) -->
        <div id="tab-about" class="tab-content">
            <div class="content-page" id="about-content"></div>
        </div>

        <footer>
            <div class="footer-content">
                <div class="footer-left">
                    <span class="footer-brand">Recall Dashboard v0.1.5</span>
                    <span class="footer-divider">|</span>
                    <span class="footer-status">
                        <span class="status-dot"></span>
                        Live Mode
                    </span>
                    <span class="footer-divider">|</span>
                    <select id="theme-selector" class="theme-dropdown" aria-label="Select theme">
                        <option value="catppuccin">Catppuccin</option>
                        <option value="catppuccin-latte">Catppuccin Latte</option>
                        <option value="everforest">Everforest</option>
                        <option value="flexoki-light">Flexoki Light</option>
                        <option value="gruvbox">Gruvbox</option>
                        <option value="kanagawa">Kanagawa</option>
                        <option value="matte-black">Matte Black</option>
                        <option value="nord">Nord</option>
                        <option value="osaka-jade">Osaka Jade</option>
                        <option value="ristretto">Ristretto</option>
                        <option value="rose-pine">Rose Pine</option>
                        <option value="tokyo-night" selected>Tokyo Night</option>
                    </select>
                </div>
                <div class="footer-right">
                    <button class="footer-link" onclick="switchTab('about')">About</button>
                    <span class="footer-divider">|</span>
                    <a class="footer-link" href="https://github.com/seheart/recall" target="_blank" rel="noopener noreferrer">GitHub</a>
                    <span class="footer-divider">|</span>
                    <span style="color: var(--muted); font-size: 11px;">Built by <a class="footer-link" href="https://setheheart.com" target="_blank" rel="noopener noreferrer">Seth Eheart</a> of <a class="footer-link" href="https://ant312.com" target="_blank" rel="noopener noreferrer">ANT</a></span>
                </div>
            </div>
        </footer>
    </div>

    <div class="modal" id="project-modal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <div id="modal-body"></div>
        </div>
    </div>

    <script>
        let projectsData = {{ projects_json | safe }};
        let tagsData = {{ tags_json | safe }};
        // projectDetails now loaded on-demand via /api/project/<name> (lazy loading)
        const projectDetailsCache = {};  // Cache loaded project details

        // Configuration constants
        const SEARCH_DEBOUNCE_MS = {{ search_debounce_ms }};
        const MAX_PROJECT_CACHE_SIZE = {{ max_cache_size }};

        let currentFilter = null;
        let currentSearch = '';
        let currentSort = 'name-asc';
        let currentTab = 'projects';

        // Tab switching function
        function switchTab(tabName) {
            currentTab = tabName;

            // Update tab buttons
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
                if (btn.dataset.tab === tabName) {
                    btn.classList.add('active');
                }
            });

            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });

            const tabContent = document.getElementById(`tab-${tabName}`);
            if (tabContent) {
                tabContent.classList.add('active');
            }

            // Load content for specific tabs
            if (tabName === 'insights') {
                loadInsightsContent();
            } else if (tabName === 'activity') {
                loadActivityContent();
            } else if (tabName === 'how-to-use') {
                loadHowToUseContent();
            } else if (tabName === 'about') {
                loadAboutContent();
            }
        }

        // Add tab click handlers
        document.addEventListener('DOMContentLoaded', () => {
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.addEventListener('click', () => {
                    switchTab(btn.dataset.tab);
                });
            });

            // Keyboard shortcuts for tabs
            document.addEventListener('keydown', (e) => {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

                switch(e.key) {
                    case '1': switchTab('projects'); break;
                    case '2': switchTab('insights'); break;
                    case '3': switchTab('activity'); break;
                    case '4': switchTab('how-to-use'); break;
                }
            });
        });

        // XSS Protection: Escape HTML in user-provided content
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Calculate project status based on last update
        function getProjectStatus(updatedAt) {
            if (!updatedAt) return { badge: '⚪', label: 'Unknown', class: 'status-unknown' };

            const now = new Date();
            const updated = new Date(updatedAt);
            const daysSince = Math.floor((now - updated) / (1000 * 60 * 60 * 24));

            if (daysSince <= 7) {
                return { badge: '🟢', label: 'Active', class: 'status-active', days: daysSince };
            } else if (daysSince <= 30) {
                return { badge: '🟡', label: 'Idle', class: 'status-idle', days: daysSince };
            } else {
                return { badge: '🔴', label: 'Stale', class: 'status-stale', days: daysSince };
            }
        }

        // Convert timestamp to relative time (e.g., "3 days ago")
        function getRelativeTime(timestamp) {
            if (!timestamp) return 'Unknown';

            const now = new Date();
            const past = new Date(timestamp);
            const secondsAgo = Math.floor((now - past) / 1000);
            const minutesAgo = Math.floor(secondsAgo / 60);
            const hoursAgo = Math.floor(minutesAgo / 60);
            const daysAgo = Math.floor(hoursAgo / 24);
            const weeksAgo = Math.floor(daysAgo / 7);
            const monthsAgo = Math.floor(daysAgo / 30);
            const yearsAgo = Math.floor(daysAgo / 365);

            if (secondsAgo < 60) return 'Just now';
            if (minutesAgo < 60) return `${minutesAgo} minute${minutesAgo !== 1 ? 's' : ''} ago`;
            if (hoursAgo < 24) return `${hoursAgo} hour${hoursAgo !== 1 ? 's' : ''} ago`;
            if (daysAgo < 7) return `${daysAgo} day${daysAgo !== 1 ? 's' : ''} ago`;
            if (weeksAgo < 4) return `${weeksAgo} week${weeksAgo !== 1 ? 's' : ''} ago`;
            if (monthsAgo < 12) return `${monthsAgo} month${monthsAgo !== 1 ? 's' : ''} ago`;
            return `${yearsAgo} year${yearsAgo !== 1 ? 's' : ''} ago`;
        }

        // Theme switcher
        const themeSelector = document.getElementById('theme-selector');
        if (themeSelector) {
            themeSelector.addEventListener('change', (e) => {
                const theme = e.target.value;
                document.body.className = `theme--${theme}`;
                localStorage.setItem('recall-theme', theme);
            });

            // Load saved theme or default to tokyo-night
            let savedTheme = localStorage.getItem('recall-theme');
            if (!savedTheme) {
                savedTheme = 'tokyo-night';
            }
            document.body.className = `theme--${savedTheme}`;
            themeSelector.value = savedTheme;
        }

        // WebSocket connection for live updates with reconnection logic
        const socket = io();
        let reconnectAttempts = 0;
        const MAX_RECONNECT_ATTEMPTS = 10;

        socket.on('connect', function() {
            console.log('✅ Connected to live updates');
            reconnectAttempts = 0;  // Reset on successful connection
        });

        socket.on('disconnect', function() {
            console.log('⚠️ Disconnected from live updates');
            attemptReconnect();
        });

        function attemptReconnect() {
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                console.log(`🔄 Reconnecting in ${delay/1000}s (attempt ${reconnectAttempts + 1})`);
                setTimeout(() => {
                    reconnectAttempts++;
                    socket.connect();
                }, delay);
            } else {
                console.log('❌ Max reconnection attempts reached');
            }
        }

        socket.on('data_update', function(data) {
            console.log('📡 Received live update:', data.timestamp);

            // Clear stale cache
            Object.keys(projectDetailsCache).forEach(key => delete projectDetailsCache[key]);

            // Update data
            projectsData = data.projects;
            tagsData = data.tags;

            // Re-render with new data
            updateStats();
            renderProjects();
            renderTagFilters();
        });

        // Calculate statistics
        function updateStats() {
            const totalProjects = projectsData.length;
            const totalSessions = projectsData.reduce((sum, p) => sum + p.session_count, 0);
            const totalContext = projectsData.reduce((sum, p) => sum + p.context_count, 0);
            const totalTags = tagsData.length;

            document.getElementById('total-projects').textContent = totalProjects;
            document.getElementById('total-sessions').textContent = totalSessions;
            document.getElementById('total-context').textContent = totalContext;
            document.getElementById('total-tags').textContent = totalTags;
        }

        // Render tag filters
        function renderTagFilters() {
            const container = document.getElementById('tag-filters');
            container.innerHTML = `<div class="tag-filter active" data-tag="all">All Projects (${projectsData.length})</div>`;

            tagsData.forEach(tagData => {
                const tagEl = document.createElement('div');
                tagEl.className = 'tag-filter';
                tagEl.dataset.tag = tagData.tag;
                tagEl.textContent = `${tagData.tag} (${tagData.count})`;
                tagEl.addEventListener('click', () => filterByTag(tagData.tag));
                container.appendChild(tagEl);
            });

            container.firstChild.addEventListener('click', () => filterByTag(null));
        }

        // Filter by tag
        function filterByTag(tag) {
            currentFilter = tag;
            document.querySelectorAll('.tag-filter').forEach(el => {
                el.classList.remove('active');
                if ((tag === null && el.dataset.tag === 'all') || el.dataset.tag === tag) {
                    el.classList.add('active');
                }
            });
            renderProjects();
        }

        // Search projects with debouncing
        let searchDebounceTimer = null;

        document.getElementById('search').addEventListener('input', (e) => {
            clearTimeout(searchDebounceTimer);
            const searchValue = e.target.value.toLowerCase();
            searchDebounceTimer = setTimeout(() => {
                currentSearch = searchValue;
                renderProjects();
            }, SEARCH_DEBOUNCE_MS);
        });

        // Sort projects
        document.getElementById('sort-select').addEventListener('change', (e) => {
            currentSort = e.target.value;
            renderProjects();
        });

        // Clear all filters
        document.getElementById('clear-filters').addEventListener('click', () => {
            currentFilter = null;
            currentSearch = '';
            currentSort = 'name-asc';
            document.getElementById('search').value = '';
            document.getElementById('sort-select').value = 'name-asc';
            renderProjects();
            renderTagFilters();
        });

        // Sorting function
        function sortProjects(projects, sortBy) {
            const sorted = [...projects];

            switch(sortBy) {
                case 'name-asc':
                    return sorted.sort((a, b) => a.name.localeCompare(b.name));
                case 'name-desc':
                    return sorted.sort((a, b) => b.name.localeCompare(a.name));
                case 'updated-desc':
                    return sorted.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
                case 'updated-asc':
                    return sorted.sort((a, b) => new Date(a.updated_at) - new Date(b.updated_at));
                case 'sessions-desc':
                    return sorted.sort((a, b) => b.session_count - a.session_count);
                case 'sessions-asc':
                    return sorted.sort((a, b) => a.session_count - b.session_count);
                case 'context-desc':
                    return sorted.sort((a, b) => b.context_count - a.context_count);
                case 'context-asc':
                    return sorted.sort((a, b) => a.context_count - b.context_count);
                default:
                    return sorted;
            }
        }

        // Render projects
        function renderProjects() {
            const container = document.getElementById('projects-grid');

            // Check if there are no projects at all (empty state)
            if (projectsData.length === 0) {
                container.innerHTML = `
                    <div class="no-results">
                        <div style="font-size: 48px; margin-bottom: 16px;">🧠</div>
                        <div style="font-size: 16px; font-weight: 600; margin-bottom: 8px; color: var(--text-heading);">
                            Welcome to Recall!
                        </div>
                        <div style="margin-bottom: 16px; line-height: 1.6;">
                            No projects found. Get started by creating your first project.
                        </div>
                        <div style="text-align: left; max-width: 500px; margin: 0 auto; background: var(--surface-2); padding: 16px; border-radius: var(--radius); border: 1px solid var(--border);">
                            <div style="font-weight: 600; margin-bottom: 8px; color: var(--accent);">Quick Start:</div>
                            <div style="font-family: var(--mono); font-size: 11px; margin-bottom: 6px;">
                                <span style="color: var(--muted);">$</span> recall myproject --create
                            </div>
                            <div style="font-family: var(--mono); font-size: 11px; margin-bottom: 6px;">
                                <span style="color: var(--muted);">$</span> recall myproject --analyze
                            </div>
                            <div style="font-family: var(--mono); font-size: 11px;">
                                <span style="color: var(--muted);">$</span> recall myproject --git-log --days 30
                            </div>
                            <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); font-size: 11px; color: var(--muted);">
                                💡 Then refresh this dashboard to see your project!
                            </div>
                        </div>
                    </div>
                `;
                return;
            }

            let filtered = projectsData.filter(project => {
                if (currentFilter) {
                    const projectTags = project.tags ? project.tags.split(',') : [];
                    if (!projectTags.includes(currentFilter)) return false;
                }

                if (currentSearch) {
                    const searchable = `${project.name} ${project.description || ''} ${project.tags || ''}`.toLowerCase();
                    if (!searchable.includes(currentSearch)) return false;
                }

                return true;
            });

            // Apply sorting
            filtered = sortProjects(filtered, currentSort);

            // Update search results count
            const resultsCount = document.getElementById('search-results-count');
            if (currentSearch || currentFilter) {
                resultsCount.textContent = `Showing ${filtered.length} of ${projectsData.length} projects`;
                resultsCount.style.display = 'block';
            } else {
                resultsCount.textContent = '';
                resultsCount.style.display = 'none';
            }

            if (filtered.length === 0) {
                container.innerHTML = '<div class="no-results">No projects match your search or filter</div>';
                return;
            }

            container.innerHTML = filtered.map(project => {
                const tags = project.tags ? project.tags.split(',').map(tag =>
                    `<span class="tag">${escapeHtml(tag)}</span>`
                ).join('') : '<span style="color: #999; font-size: 0.85em;">No tags</span>';

                const description = project.description
                    ? `<div class="project-description">${escapeHtml(project.description)}</div>`
                    : '';

                const status = getProjectStatus(project.updated_at);
                const statusBadge = `<span class="status-badge ${status.class}" title="${status.label}: Recalled ${status.days} days ago">${status.badge}</span>`;

                return `
                    <div class="project-card"
                         role="button"
                         tabindex="0"
                         onclick="showProjectDetails('${escapeHtml(project.name)}')"
                         onkeypress="if(event.key==='Enter'||event.key===' ')showProjectDetails('${escapeHtml(project.name)}')"
                         aria-label="View details for ${escapeHtml(project.name)} project">
                        <div class="project-header">
                            <div>
                                <div class="project-name">${escapeHtml(project.name)} ${statusBadge}</div>
                            </div>
                        </div>
                        ${description}
                        <div class="project-path">📁 ${escapeHtml(project.directory)}</div>
                        <div class="project-tags">${tags}</div>
                        <div class="project-stats">
                            <div class="project-stat">
                                <div class="project-stat-number">${project.session_count}</div>
                                <div class="project-stat-label tooltip" data-tooltip="Sessions">Sessions</div>
                            </div>
                            <div class="project-stat">
                                <div class="project-stat-number">${project.context_count}</div>
                                <div class="project-stat-label tooltip" data-tooltip="Context">Context</div>
                            </div>
                            <div class="project-stat">
                                <div class="project-stat-number">${project.tags ? project.tags.split(',').length : 0}</div>
                                <div class="project-stat-label tooltip" data-tooltip="Tags">Tags</div>
                            </div>
                        </div>
                        <div class="project-date" title="Last recalled: ${escapeHtml(project.updated_at)}" style="cursor: help;">
                            Recalled ${getRelativeTime(project.updated_at)}
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Modal functions
        // Cache management with size enforcement
        function addToCache(projectName, details) {
            // Implement LRU cache eviction
            const cacheKeys = Object.keys(projectDetailsCache);
            if (cacheKeys.length >= MAX_PROJECT_CACHE_SIZE) {
                // Remove oldest entry (first key)
                delete projectDetailsCache[cacheKeys[0]];
            }
            projectDetailsCache[projectName] = details;
        }

        // Lazy loading: Fetch project details on demand
        async function showProjectDetails(projectName) {
            const project = projectsData.find(p => p.name === projectName);
            if (!project) return;

            // Show loading state
            document.getElementById('modal-body').innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 64px;">
                    <div style="font-size: 48px; margin-bottom: 16px;">⏳</div>
                    <div style="font-size: 14px; color: var(--muted);">Loading project details...</div>
                </div>
            `;
            document.getElementById('project-modal').classList.add('active');

            // Fetch details from API (or use cache)
            try {
                let details = projectDetailsCache[projectName];
                if (!details) {
                    const response = await fetch(`/api/project/${encodeURIComponent(projectName)}`);
                    if (!response.ok) throw new Error('Failed to load project details');
                    details = await response.json();
                    addToCache(projectName, details);  // Cache with size enforcement
                }

                // Fetch enriched context
                let enriched = {};
                try {
                    const enrichedResponse = await fetch(`/api/project/${encodeURIComponent(projectName)}/enriched`);
                    if (enrichedResponse.ok) {
                        const enrichedData = await enrichedResponse.json();
                        enriched = enrichedData.enriched || {};
                    }
                } catch (e) {
                    console.warn('Failed to fetch enriched context:', e);
                }

            let html = `
                <div class="modal-header">
                    <div class="modal-title">${escapeHtml(project.name).toUpperCase()}</div>
                    <div class="modal-subtitle">${escapeHtml(project.description) || 'No description'}</div>
                    <div class="modal-subtitle">📁 ${escapeHtml(project.directory)}</div>
                    <div class="modal-subtitle">Updated: ${escapeHtml(project.updated_at)}</div>
                </div>
            `;

            // Display enriched current state
            if (enriched.current_state) {
                const state = enriched.current_state;
                html += `
                    <div class="context-section">
                        <div class="context-section-title">📍 CURRENT STATE</div>
                        <div class="context-items">
                            ${state.status ? `<div class="context-item"><span class="context-key">Status:</span>${escapeHtml(state.status)}</div>` : ''}
                            ${state.last_active ? `<div class="context-item"><span class="context-key">Last Active:</span>${escapeHtml(state.last_active)}</div>` : ''}
                            ${state.health ? `<div class="context-item"><span class="context-key">Health:</span>${state.health_emoji || ''} ${escapeHtml(state.health)}</div>` : ''}
                        </div>
                    </div>
                `;
            }

            // Display TODOs and issues
            if (enriched.todos_and_issues && enriched.todos_and_issues.total > 0) {
                const todos = enriched.todos_and_issues;
                html += `
                    <div class="context-section">
                        <div class="context-section-title">📝 TODO & ISSUES (${todos.total})</div>
                        <div class="context-items">
                `;

                if (todos.fixme && todos.fixme.length > 0) {
                    todos.fixme.forEach(item => {
                        html += `<div class="context-item"><span class="context-key">FIXME:</span>${escapeHtml(item.file)}:${item.line} - ${escapeHtml(item.text)}</div>`;
                    });
                }

                if (todos.todo && todos.todo.length > 0) {
                    todos.todo.forEach(item => {
                        html += `<div class="context-item"><span class="context-key">TODO:</span>${escapeHtml(item.file)}:${item.line} - ${escapeHtml(item.text)}</div>`;
                    });
                }

                if (todos.hack && todos.hack.length > 0) {
                    todos.hack.forEach(item => {
                        html += `<div class="context-item"><span class="context-key">HACK:</span>${escapeHtml(item.file)}:${item.line} - ${escapeHtml(item.text)}</div>`;
                    });
                }

                html += `
                        </div>
                    </div>
                `;
            }

            // Display key files
            if (enriched.key_files && enriched.key_files.length > 0) {
                html += `
                    <div class="context-section">
                        <div class="context-section-title">📁 KEY FILES (Recently Modified)</div>
                        <div class="context-items">
                `;

                enriched.key_files.forEach(file => {
                    html += `<div class="context-item"><span class="context-key">${escapeHtml(file.path)}:</span>${file.modifications} change(s), last ${escapeHtml(file.last_modified)}</div>`;
                });

                html += `
                        </div>
                    </div>
                `;
            }

            // Display quick commands
            if (enriched.quick_commands && Object.keys(enriched.quick_commands).length > 0) {
                html += `
                    <div class="context-section">
                        <div class="context-section-title">🔧 QUICK COMMANDS</div>
                        <div class="context-items">
                `;

                Object.entries(enriched.quick_commands).forEach(([key, cmd]) => {
                    html += `<div class="context-item"><span class="context-key">${key}:</span><code style="font-family: var(--mono); background: var(--code-bg); padding: 2px 6px; border-radius: 2px;">${escapeHtml(cmd)}</code></div>`;
                });

                html += `
                        </div>
                    </div>
                `;
            }

            // Display warnings
            if (enriched.warnings && enriched.warnings.length > 0) {
                html += `
                    <div class="context-section">
                        <div class="context-section-title">⚠️ WARNINGS</div>
                        <div class="context-items">
                `;

                enriched.warnings.forEach(warning => {
                    html += `<div class="context-item" style="color: var(--warning);">${escapeHtml(warning)}</div>`;
                });

                html += `
                        </div>
                    </div>
                `;
            }

            // Display suggestions
            if (enriched.suggestions && enriched.suggestions.length > 0) {
                html += `
                    <div class="context-section">
                        <div class="context-section-title">💡 SUGGESTIONS</div>
                        <div class="context-items">
                `;

                enriched.suggestions.forEach(suggestion => {
                    html += `<div class="context-item">${escapeHtml(suggestion)}</div>`;
                });

                html += `
                        </div>
                    </div>
                `;
            }

            // Continue with original context sections below
            const contextCategories = Object.keys(details.context);
            if (contextCategories.length > 0) {
                contextCategories.forEach(category => {
                    const categoryName = category.replace(/_/g, ' ').toUpperCase();
                    const icon = getCategoryIcon(category);
                    html += `
                        <div class="context-section">
                            <div class="context-section-title">${icon} ${categoryName}</div>
                            <div class="context-items">
                    `;

                    details.context[category].forEach(item => {
                        const key = item.key.replace(/_/g, ' ');
                        html += `<div class="context-item"><span class="context-key">${escapeHtml(key)}:</span>${escapeHtml(item.value)}</div>`;
                    });

                    html += `</div></div>`;
                });
            } else {
                html += `<div class="no-data">No context data. Run <code>recall ${projectName} --analyze</code></div>`;
            }

            if (details.sessions && details.sessions.length > 0) {
                html += '<div class="context-section"><div class="context-section-title">📝 RECENT SESSIONS</div>';

                details.sessions.forEach((session, index) => {
                    html += `
                        <div class="session-card">
                            <div class="session-date">Session ${index + 1} - ${escapeHtml(session.created_at)}</div>
                    `;

                    if (session.summary) html += `<div class="session-detail"><span class="session-label">Summary:</span> ${escapeHtml(session.summary)}</div>`;
                    if (session.accomplishments) html += `<div class="session-detail"><span class="session-label">Accomplishments:</span> ${escapeHtml(session.accomplishments)}</div>`;
                    if (session.decisions_made) html += `<div class="session-detail"><span class="session-label">Decisions:</span> ${escapeHtml(session.decisions_made)}</div>`;
                    if (session.next_steps) html += `<div class="session-detail"><span class="session-label">Next Steps:</span> ${escapeHtml(session.next_steps)}</div>`;

                    html += '</div>';
                });

                html += '</div>';
            } else {
                html += '<div class="context-section"><div class="context-section-title">📝 RECENT SESSIONS</div><div class="no-data">No sessions logged yet.</div></div>';
            }

            // Add export/action buttons
            html += `
                <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--border); display: flex; gap: 8px; flex-wrap: wrap;">
                    <button onclick="exportProjectJSON('${escapeHtml(projectName)}')" style="padding: 8px 16px; background: var(--accent); color: white; border: none; border-radius: var(--radius); cursor: pointer; font-family: var(--mono); font-size: 12px; min-height: 44px;">
                        📥 Export JSON
                    </button>
                    <button onclick="copyProjectToClipboard('${escapeHtml(projectName)}')" style="padding: 8px 16px; background: var(--surface-2); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius); cursor: pointer; font-family: var(--mono); font-size: 12px; min-height: 44px;">
                        📋 Copy to Clipboard
                    </button>
                    <button onclick="window.print()" style="padding: 8px 16px; background: var(--surface-2); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius); cursor: pointer; font-family: var(--mono); font-size: 12px; min-height: 44px;">
                        🖨️ Print
                    </button>
                </div>
            `;

            document.getElementById('modal-body').innerHTML = html;
            // Modal already opened above with loading state
            } catch (error) {
                console.error('Error loading project details:', error);
                document.getElementById('modal-body').innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 64px;">
                        <div style="font-size: 48px; margin-bottom: 16px;">❌</div>
                        <div style="font-size: 14px; color: var(--error);">Failed to load project details</div>
                        <div style="font-size: 12px; color: var(--muted); margin-top: 8px;">${error.message}</div>
                    </div>
                `;
            }
        }

        function closeModal() {
            document.getElementById('project-modal').classList.remove('active');
        }

        // Export project data as JSON file
        function exportProjectJSON(projectName) {
            const project = projectsData.find(p => p.name === projectName);
            const details = projectDetailsCache[projectName];

            if (!project || !details) {
                alert('Project details not loaded yet');
                return;
            }

            const exportData = {
                name: project.name,
                description: project.description,
                directory: project.directory,
                updated_at: project.updated_at,
                session_count: project.session_count,
                context_count: project.context_count,
                tags: project.tags ? project.tags.split(',') : [],
                context: details.context,
                sessions: details.sessions
            };

            const dataStr = JSON.stringify(exportData, null, 2);
            const dataBlob = new Blob([dataStr], { type: 'application/json' });
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${projectName}-recall-export.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        }

        // Copy project data to clipboard (formatted for Claude Code)
        function copyProjectToClipboard(projectName) {
            const project = projectsData.find(p => p.name === projectName);
            const details = projectDetailsCache[projectName];

            if (!project || !details) {
                alert('Project details not loaded yet');
                return;
            }

            let text = `# ${project.name}\n\n`;
            if (project.description) text += `${project.description}\n\n`;
            text += `**Directory:** ${project.directory}\n`;
            text += `**Updated:** ${project.updated_at}\n`;
            text += `**Sessions:** ${project.session_count} | **Context:** ${project.context_count}\n\n`;

            if (project.tags) {
                text += `**Tags:** ${project.tags}\n\n`;
            }

            text += `## Context\n\n`;
            const contextCategories = Object.keys(details.context);
            contextCategories.forEach(category => {
                text += `### ${category.replace(/_/g, ' ').toUpperCase()}\n\n`;
                details.context[category].forEach(item => {
                    text += `- **${item.key.replace(/_/g, ' ')}:** ${item.value}\n`;
                });
                text += `\n`;
            });

            if (details.sessions && details.sessions.length > 0) {
                text += `## Recent Sessions\n\n`;
                details.sessions.forEach((session, index) => {
                    text += `### Session ${index + 1} (${session.created_at})\n\n`;
                    if (session.summary) text += `**Summary:** ${session.summary}\n\n`;
                    if (session.accomplishments) text += `**Accomplishments:** ${session.accomplishments}\n\n`;
                    if (session.decisions_made) text += `**Decisions:** ${session.decisions_made}\n\n`;
                    if (session.next_steps) text += `**Next Steps:** ${session.next_steps}\n\n`;
                });
            }

            navigator.clipboard.writeText(text).then(() => {
                alert('Project data copied to clipboard!');
            }).catch(err => {
                console.error('Failed to copy:', err);
                alert('Failed to copy to clipboard');
            });
        }

        // Load inline content functions
        function loadInsightsContent() {
            const container = document.getElementById('insights-content');
            showInsightsInline(container);
        }

        function loadActivityContent() {
            const container = document.getElementById('activity-content');
            showRecentActivityInline(container);
        }

        function loadHowToUseContent() {
            const container = document.getElementById('how-to-use-content');
            container.innerHTML = getHowToUseHTML();
        }

        function loadAboutContent() {
            const container = document.getElementById('about-content');
            container.innerHTML = getAboutHTML();
        }

        // Show cross-project insights (inline version)
        function showInsightsInline(container) {
            // Calculate aggregate statistics
            const totalProjects = projectsData.length;
            const totalSessions = projectsData.reduce((sum, p) => sum + p.session_count, 0);
            const totalContext = projectsData.reduce((sum, p) => sum + p.context_count, 0);
            const avgSessions = totalProjects > 0 ? (totalSessions / totalProjects).toFixed(1) : 0;
            const avgContext = totalProjects > 0 ? (totalContext / totalProjects).toFixed(1) : 0;

            // Tag frequency
            const tagCounts = {};
            projectsData.forEach(project => {
                if (project.tags) {
                    project.tags.split(',').forEach(tag => {
                        tagCounts[tag] = (tagCounts[tag] || 0) + 1;
                    });
                }
            });
            const sortedTags = Object.entries(tagCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10);

            // Activity analysis
            const activeProjects = projectsData.filter(p => {
                const status = getProjectStatus(p.updated_at);
                return status.label === 'Active';
            }).length;
            const idleProjects = projectsData.filter(p => {
                const status = getProjectStatus(p.updated_at);
                return status.label === 'Idle';
            }).length;
            const staleProjects = projectsData.filter(p => {
                const status = getProjectStatus(p.updated_at);
                return status.label === 'Stale';
            }).length;

            // Most/least active projects
            const mostActive = [...projectsData].sort((a, b) => b.session_count - a.session_count).slice(0, 5);
            const mostDocumented = [...projectsData].sort((a, b) => b.context_count - a.context_count).slice(0, 5);

            container.innerHTML = `
                <div class="content-page">
                    <h1>📊 Cross-Project Insights</h1>
                    <p style="color: var(--muted); margin-bottom: 24px;">Analytics across all ${totalProjects} projects</p>

                    <h2>📈 Overall Statistics</h2>
                    <div class="context-items" style="background: var(--surface-2); padding: 12px; border-radius: var(--radius); border: 1px solid var(--border); margin-bottom: 24px;">
                        <div class="context-item"><span class="context-key">Total Projects:</span>${totalProjects}</div>
                        <div class="context-item"><span class="context-key">Total Sessions:</span>${totalSessions}</div>
                        <div class="context-item"><span class="context-key">Total Context Items:</span>${totalContext}</div>
                        <div class="context-item"><span class="context-key">Avg Sessions/Project:</span>${avgSessions}</div>
                        <div class="context-item"><span class="context-key">Avg Context/Project:</span>${avgContext}</div>
                    </div>

                    <h2>⚡ Activity Breakdown</h2>
                    <div class="context-items" style="background: var(--surface-2); padding: 12px; border-radius: var(--radius); border: 1px solid var(--border); margin-bottom: 24px;">
                        <div class="context-item"><span class="context-key">🟢 Active (≤7 days):</span>${activeProjects} projects</div>
                        <div class="context-item"><span class="context-key">🟡 Idle (7-30 days):</span>${idleProjects} projects</div>
                        <div class="context-item"><span class="context-key">🔴 Stale (>30 days):</span>${staleProjects} projects</div>
                    </div>

                    <h2>🏷️ Top Tags</h2>
                    <div class="context-items" style="background: var(--surface-2); padding: 12px; border-radius: var(--radius); border: 1px solid var(--border); margin-bottom: 24px;">
                        ${sortedTags.map(([tag, count]) => `
                            <div class="context-item"><span class="context-key">${escapeHtml(tag)}:</span>${count} project${count !== 1 ? 's' : ''}</div>
                        `).join('')}
                    </div>

                    <h2>🔥 Most Active Projects</h2>
                    <div class="context-items" style="background: var(--surface-2); padding: 12px; border-radius: var(--radius); border: 1px solid var(--border); margin-bottom: 24px;">
                        ${mostActive.map((p, i) => `
                            <div class="context-item"><span class="context-key">${i + 1}. ${escapeHtml(p.name)}:</span>${p.session_count} sessions</div>
                        `).join('')}
                    </div>

                    <h2>📚 Most Documented Projects</h2>
                    <div class="context-items" style="background: var(--surface-2); padding: 12px; border-radius: var(--radius); border: 1px solid var(--border);">
                        ${mostDocumented.map((p, i) => `
                            <div class="context-item"><span class="context-key">${i + 1}. ${escapeHtml(p.name)}:</span>${p.context_count} context items</div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // Show recent activity feed (inline version)
        async function showRecentActivityInline(container) {
            // Show loading state
            container.innerHTML = `
                <div class="content-page">
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 64px;">
                        <div style="font-size: 48px; margin-bottom: 16px;">⏳</div>
                        <div style="font-size: 14px; color: var(--muted);">Loading recent activity...</div>
                    </div>
                </div>
            `;

            try {
                const response = await fetch('/api/recent-activity');
                if (!response.ok) throw new Error('Failed to load activity');
                const data = await response.json();

                let html = `
                    <div class="content-page">
                        <h1>📰 Recent Activity</h1>
                        <p style="color: var(--muted); margin-bottom: 24px;">Latest sessions across all projects</p>
                `;

                if (data.sessions && data.sessions.length > 0) {
                    data.sessions.forEach((session, index) => {
                        const relTime = getRelativeTime(session.created_at);
                        html += `
                            <div class="session-card" style="margin-bottom: 16px;">
                                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                                    <div style="font-weight: 600; color: var(--accent);">${escapeHtml(session.project_name)}</div>
                                    <div style="font-size: 11px; color: var(--muted);" title="${escapeHtml(session.created_at)}">${relTime}</div>
                                </div>
                        `;

                        if (session.summary) html += `<div class="session-detail"><span class="session-label">Summary:</span> ${escapeHtml(session.summary)}</div>`;
                        if (session.accomplishments) html += `<div class="session-detail"><span class="session-label">Accomplishments:</span> ${escapeHtml(session.accomplishments)}</div>`;
                        if (session.decisions_made) html += `<div class="session-detail"><span class="session-label">Decisions:</span> ${escapeHtml(session.decisions_made)}</div>`;
                        if (session.next_steps) html += `<div class="session-detail"><span class="session-label">Next Steps:</span> ${escapeHtml(session.next_steps)}</div>`;

                        html += '</div>';
                    });
                } else {
                    html += '<div class="no-data">No recent activity found</div>';
                }

                html += '</div>';
                container.innerHTML = html;
            } catch (error) {
                console.error('Error loading recent activity:', error);
                container.innerHTML = `
                    <div class="content-page">
                        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 64px;">
                            <div style="font-size: 48px; margin-bottom: 16px;">❌</div>
                            <div style="font-size: 14px; color: var(--error);">Failed to load activity</div>
                        </div>
                    </div>
                `;
            }
        }

        // Get How To Use HTML content
        function getHowToUseHTML() {
            return `
                <h1>📘 How to Use Recall</h1>

                <h2>Quick Start</h2>

                <h3>1. Create Your First Project</h3>
                <pre><code>recall myproject --create</code></pre>
                <p>This creates a new project entry in the Recall database.</p>

                <h3>2. Analyze Your Project</h3>
                <pre><code>recall myproject --analyze</code></pre>
                <p>Automatically detects and stores:</p>
                <ul>
                    <li>Tech stack (Node.js, Python, Rust, etc.)</li>
                    <li>Package manager and dependencies</li>
                    <li>Git repository info and status</li>
                    <li>Directory structure</li>
                    <li>Environment configuration</li>
                </ul>

                <h3>3. Log Git History as Sessions</h3>
                <pre><code>recall myproject --git-log --days 30</code></pre>
                <p>Imports recent git commits as development sessions, preserving your work history.</p>

                <h2>Common Commands</h2>

                <h3>View Project Status</h3>
                <pre><code>recall myproject</code></pre>
                <p>Shows all stored context and recent sessions for the project.</p>

                <h3>Add Custom Context</h3>
                <pre><code>recall myproject --add-context architecture "Microservices with Docker"</code></pre>
                <p>Store custom notes, decisions, or architectural details.</p>

                <h3>Add Tags</h3>
                <pre><code>recall myproject --add-tag web --add-tag react --add-tag api</code></pre>
                <p>Categorize projects for easy filtering in the dashboard.</p>

                <h3>View All Projects</h3>
                <pre><code>recall --list</code></pre>
                <p>List all tracked projects with their stats.</p>

                <h2>Dashboard Usage</h2>

                <h3>Start the Live Dashboard</h3>
                <pre><code>python3 dashboard_app.py</code></pre>
                <p>Launches the Flask web server at <code>http://127.0.0.1:5000</code></p>

                <div class="note-box">
                    <strong>💡 Pro Tip:</strong> The dashboard auto-refreshes every 30 seconds. Any changes you make
                    via the CLI will appear automatically without manual refresh!
                </div>

                <h3>Dashboard Features</h3>
                <ul>
                    <li><strong>Search</strong> - Filter projects by name, description, or tags</li>
                    <li><strong>Tag Filters</strong> - Click tags to filter by technology or type</li>
                    <li><strong>Sort Options</strong> - Sort by name, recent activity, sessions, or context</li>
                    <li><strong>Project Details</strong> - Click any project card to view full context and sessions</li>
                    <li><strong>Insights</strong> - View cross-project analytics and statistics</li>
                    <li><strong>Activity Feed</strong> - See recent development sessions across all projects</li>
                </ul>

                <h3>Keyboard Shortcuts</h3>
                <ul>
                    <li><code>1</code> - Projects tab</li>
                    <li><code>2</code> - Insights tab</li>
                    <li><code>3</code> - Activity tab</li>
                    <li><code>4</code> - How to Use tab</li>
                    <li><code>/</code> - Focus search bar</li>
                    <li><code>Esc</code> - Close modal</li>
                    <li><code>r</code> - Refresh dashboard</li>
                </ul>

                <h2>Integration with Claude Code</h2>

                <p>When working with Claude Code, you can paste project context directly from Recall:</p>
                <ol>
                    <li>Open a project in the dashboard</li>
                    <li>Click "Copy to Clipboard"</li>
                    <li>Paste into your Claude Code conversation</li>
                </ol>
                <p>This gives Claude perfect memory of your project's architecture, decisions, and recent work!</p>

                <div class="note-box">
                    <strong>🚀 Next Steps:</strong> Run <code>recall --help</code> to see all available commands,
                    or check out the <a href="https://github.com/seheart/recall" target="_blank" style="color: var(--accent);">GitHub README</a>
                    for detailed documentation.
                </div>
            `;
        }

        // Get About HTML content
        function getAboutHTML() {
            return `
                <h1>🧠 About Recall</h1>

                <p>
                    <strong>Recall</strong> is a project memory system designed for developers using Claude Code.
                    It automatically tracks context, decisions, and development sessions across all your projects,
                    giving Claude Code perfect memory of your work.
                </p>

                <h2>Key Features</h2>
                <ul>
                    <li><strong>Automatic Context Tracking</strong> - Detects tech stack, dependencies, git status, and more</li>
                    <li><strong>Session Logging</strong> - Auto-logs development sessions from git commits</li>
                    <li><strong>Live Dashboard</strong> - Real-time web interface with auto-refresh</li>
                    <li><strong>Cross-Project Insights</strong> - View analytics across all your projects</li>
                    <li><strong>Claude Code Integration</strong> - Seamlessly works with your AI coding workflow</li>
                    <li><strong>Tag System</strong> - Organize projects by technology, type, or custom labels</li>
                </ul>

                <h2>How It Works</h2>
                <p>
                    Recall maintains a SQLite database at <code>~/.local/share/recall/projects.db</code> containing:
                </p>
                <ul>
                    <li><strong>Projects</strong> - Each project you're tracking</li>
                    <li><strong>Context</strong> - Architecture, decisions, environment details, git info, etc.</li>
                    <li><strong>Sessions</strong> - Development sessions with accomplishments and next steps</li>
                    <li><strong>Tags</strong> - Categorization for easy filtering</li>
                </ul>

                <h2>Technology</h2>
                <p>
                    Built with Python 3, SQLite, and Flask. The dashboard uses vanilla JavaScript with
                    no external dependencies for maximum performance and simplicity.
                </p>

                <h2>Open Source</h2>
                <p>
                    Recall is open source and available on <a href="https://github.com/seheart/recall" target="_blank" style="color: var(--accent);">GitHub</a>.
                    Contributions, issues, and feature requests are welcome!
                </p>

                <p style="margin-top: 40px; padding-top: 20px; border-top: 1px solid var(--border); color: var(--muted); font-size: 11px;">
                    Built by <a href="https://setheheart.com" target="_blank" style="color: var(--accent);">Seth Eheart</a>
                    of <a href="https://ant312.com" target="_blank" style="color: var(--accent);">ANT</a>
                </p>
            `;
        }

        function getCategoryIcon(category) {
            const icons = {
                'architecture': '🏗️',
                'state': '⚡',
                'decisions': '🎯',
                'git': '📦',
                'npm': '📦',
                'structure': '📂',
                'info': 'ℹ️',
                'auto_analyzed': '🔍',
                'environment': '⚙️',
                'documentation': '📄'
            };
            return icons[category] || '•';
        }

        document.getElementById('project-modal').addEventListener('click', (e) => {
            if (e.target.id === 'project-modal') closeModal();
        });

        // Show keyboard shortcuts help
        function showKeyboardHelp() {
            const helpHtml = `
                <div class="modal-header">
                    <div class="modal-title">⌨️ Keyboard Shortcuts</div>
                </div>
                <div style="display: grid; gap: 12px; font-size: 13px;">
                    <div style="display: grid; grid-template-columns: 80px 1fr; gap: 8px; align-items: center; padding: 8px; background: var(--surface-2); border-radius: var(--radius);">
                        <kbd style="background: var(--surface); border: 1px solid var(--border); padding: 4px 8px; border-radius: 4px; font-family: var(--mono); font-size: 12px;">/</kbd>
                        <span>Focus search bar</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 80px 1fr; gap: 8px; align-items: center; padding: 8px; background: var(--surface-2); border-radius: var(--radius);">
                        <kbd style="background: var(--surface); border: 1px solid var(--border); padding: 4px 8px; border-radius: 4px; font-family: var(--mono); font-size: 12px;">Esc</kbd>
                        <span>Close modal or clear search</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 80px 1fr; gap: 8px; align-items: center; padding: 8px; background: var(--surface-2); border-radius: var(--radius);">
                        <kbd style="background: var(--surface); border: 1px solid var(--border); padding: 4px 8px; border-radius: 4px; font-family: var(--mono); font-size: 12px;">r</kbd>
                        <span>Refresh dashboard</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 80px 1fr; gap: 8px; align-items: center; padding: 8px; background: var(--surface-2); border-radius: var(--radius);">
                        <kbd style="background: var(--surface); border: 1px solid var(--border); padding: 4px 8px; border-radius: 4px; font-family: var(--mono); font-size: 12px;">1 / 2 / 3</kbd>
                        <span>Switch themes (Gruvbox / Ristretto / Tokyo Night)</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 80px 1fr; gap: 8px; align-items: center; padding: 8px; background: var(--surface-2); border-radius: var(--radius);">
                        <kbd style="background: var(--surface); border: 1px solid var(--border); padding: 4px 8px; border-radius: 4px; font-family: var(--mono); font-size: 12px;">Shift+C</kbd>
                        <span>Clear all filters</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 80px 1fr; gap: 8px; align-items: center; padding: 8px; background: var(--surface-2); border-radius: var(--radius);">
                        <kbd style="background: var(--surface); border: 1px solid var(--border); padding: 4px 8px; border-radius: 4px; font-family: var(--mono); font-size: 12px;">i</kbd>
                        <span>Show cross-project insights</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 80px 1fr; gap: 8px; align-items: center; padding: 8px; background: var(--surface-2); border-radius: var(--radius);">
                        <kbd style="background: var(--surface); border: 1px solid var(--border); padding: 4px 8px; border-radius: 4px; font-family: var(--mono); font-size: 12px;">a</kbd>
                        <span>Show recent activity feed</span>
                    </div>
                    <div style="display: grid; grid-template-columns: 80px 1fr; gap: 8px; align-items: center; padding: 8px; background: var(--surface-2); border-radius: var(--radius);">
                        <kbd style="background: var(--surface); border: 1px solid var(--border); padding: 4px 8px; border-radius: 4px; font-family: var(--mono); font-size: 12px;">?</kbd>
                        <span>Show this help</span>
                    </div>
                </div>
            `;
            document.getElementById('modal-body').innerHTML = helpHtml;
            document.getElementById('project-modal').classList.add('active');
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ignore shortcuts when typing in input fields
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                if (e.key === 'Escape') {
                    e.target.blur();
                }
                return;
            }

            switch(e.key) {
                case 'Escape':
                    closeModal();
                    break;
                case '/':
                    e.preventDefault();
                    document.getElementById('search').focus();
                    break;
                case 'r':
                    if (!e.ctrlKey && !e.metaKey) {
                        e.preventDefault();
                        location.reload();
                    }
                    break;
                case 'c':
                    if (e.shiftKey) {
                        e.preventDefault();
                        document.getElementById('clear-filters').click();
                    }
                    break;
                case 'i':
                    e.preventDefault();
                    switchTab('insights');
                    break;
                case 'a':
                    e.preventDefault();
                    switchTab('activity');
                    break;
                case '?':
                    e.preventDefault();
                    showKeyboardHelp();
                    break;
            }
        });

        // Initialize
        updateStats();
        renderTagFilters();
        filterByTag(null);
    </script>
</body>
</html>'''

@app.after_request
def add_cache_headers(response):
    """Add caching headers to improve performance"""
    response.cache_control.max_age = CACHE_MAX_AGE
    return response

@app.route('/api/recent-activity')
def get_recent_activity():
    """API endpoint to fetch recent activity across all projects"""
    try:
        db = get_db()

        # Get recent sessions across all projects (limit to 20)
        sessions_cursor = db.execute('''
            SELECT s.summary, s.accomplishments, s.decisions_made, s.next_steps,
                   datetime(s.created_at, 'localtime') as created_at,
                   p.name as project_name
            FROM sessions s
            JOIN projects p ON s.project_id = p.id
            ORDER BY s.created_at DESC
            LIMIT 20
        ''')

        sessions = [dict(row) for row in sessions_cursor.fetchall()]
        return {'sessions': sessions}
    except Exception as e:
        logger.error(f"Error fetching recent activity: {e}")
        return {'error': str(e)}, 500

@app.route('/api/project/<project_name>')
def get_project_api(project_name: str):
    """API endpoint to fetch individual project details (lazy loading)"""
    # Validate input
    if not validate_project_name(project_name):
        return {'error': 'Invalid project name'}, 400

    try:
        db = get_db()

        # Get project ID
        project = db.execute('SELECT id, name FROM projects WHERE name = ?', (project_name,)).fetchone()
        if not project:
            return {'error': 'Project not found'}, 404

        project_id = project['id']

        # Get context
        context_cursor = db.execute('''
            SELECT category, key, value
            FROM project_context
            WHERE project_id = ?
            ORDER BY category, key
        ''', (project_id,))

        context_dict = {}
        for row in context_cursor.fetchall():
            category = row['category']
            if category not in context_dict:
                context_dict[category] = []
            context_dict[category].append({
                'key': row['key'],
                'value': row['value']
            })

        # Get recent sessions (limit to MAX_RECENT_SESSIONS)
        sessions_cursor = db.execute('''
            SELECT summary, accomplishments, decisions_made, next_steps,
                   datetime(created_at, 'localtime') as created_at
            FROM sessions
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (project_id, MAX_RECENT_SESSIONS))

        sessions = [dict(row) for row in sessions_cursor.fetchall()]

        return {
            'context': context_dict,
            'sessions': sessions
        }
    except Exception as e:
        logger.error(f"Error fetching project details for {project_name}: {e}")
        return {'error': str(e)}, 500

@app.route('/api/project/<project_name>/enriched')
def get_project_enriched(project_name: str):
    """API endpoint to fetch enriched context for a project"""
    # Validate input
    if not validate_project_name(project_name):
        return {'error': 'Invalid project name'}, 400

    try:
        db = get_db()

        # Get project
        project = db.execute('SELECT id, name, directory FROM projects WHERE name = ?', (project_name,)).fetchone()
        if not project:
            return {'error': 'Project not found'}, 404

        project_dict = dict(project)
        project_dir = project_dict.get('directory')

        if not project_dir or not os.path.exists(project_dir):
            return {'error': 'Project directory not found', 'enriched': {}}, 200

        # Import enrichment modules
        from recall_lib.project_memory import ProjectMemory
        from recall_lib.context_enrichment import ContextEnricher

        # Initialize memory and enricher
        memory = ProjectMemory()
        enricher = ContextEnricher(project_dir, project_dict, memory)

        # Get enriched context
        enriched = enricher.enrich_all()

        return {'enriched': enriched}

    except Exception as e:
        logger.error(f"Error fetching enriched context for {project_name}: {e}")
        return {'error': str(e), 'enriched': {}}, 500

@app.route('/')
def dashboard():
    """Serve the dashboard with fresh data"""
    projects = get_projects_data()
    tags = get_tags_data()
    # Note: No longer loading all project details upfront (lazy loading)

    return render_template_string(
        HTML_TEMPLATE,
        projects_json=json.dumps(projects),
        tags_json=json.dumps(tags),
        auto_refresh_ms=AUTO_REFRESH_INTERVAL_MS,
        search_debounce_ms=SEARCH_DEBOUNCE_MS,
        max_cache_size=MAX_PROJECT_CACHE_SIZE
    )

# Global variable to store data hash for change detection
_last_data_hash = None
_hash_lock = threading.Lock()

def get_data_hash() -> str:
    """Get hash of current project data for change detection"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            projects = get_projects_data_direct(conn)
            # Create hash of project data
            data_str = json.dumps(projects, sort_keys=True)
            return hashlib.md5(data_str.encode()).hexdigest()
    except Exception as e:
        logger.error(f"Error getting data hash: {e}")
        return ""

def get_projects_data_direct(conn) -> List[Dict]:
    """Get projects data directly from connection (for background thread)"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT
            p.id,
            p.name,
            p.description,
            p.directory,
            p.created_at,
            p.updated_at,
            GROUP_CONCAT(DISTINCT t.tag) as tags,
            COUNT(DISTINCT s.id) as session_count,
            COUNT(DISTINCT c.id) as context_count
        FROM projects p
        LEFT JOIN project_tags t ON p.id = t.project_id
        LEFT JOIN sessions s ON p.id = s.project_id
        LEFT JOIN project_context c ON p.id = c.project_id
        GROUP BY p.id
        ORDER BY p.updated_at DESC
    ''')

    projects = []
    for row in cursor.fetchall():
        project = dict(row)
        projects.append(project)

    return projects

def monitor_changes():
    """Background thread to monitor database changes and emit updates"""
    global _last_data_hash
    logger.info("Starting change monitor thread")

    while True:
        try:
            current_hash = get_data_hash()

            with _hash_lock:
                if _last_data_hash is None:
                    _last_data_hash = current_hash
                elif current_hash != _last_data_hash:
                    logger.info("Data changed, emitting update to clients")
                    _last_data_hash = current_hash

                    # Get fresh data and emit to all connected clients
                    with sqlite3.connect(DB_PATH) as conn:
                        conn.row_factory = sqlite3.Row
                        projects = get_projects_data_direct(conn)
                        tags = get_tags_data_direct(conn)

                        socketio.emit('data_update', {
                            'projects': projects,
                            'tags': tags,
                            'timestamp': datetime.now(CHICAGO_TZ).strftime('%m/%d/%Y, %H:%M:%S')
                        }, broadcast=True)

            time.sleep(CHANGE_POLL_INTERVAL_SECONDS)

        except Exception as e:
            logger.error(f"Error in change monitor: {e}")
            time.sleep(ERROR_RETRY_INTERVAL_SECONDS)

def get_tags_data_direct(conn) -> List[Dict]:
    """Get tags data directly from connection"""
    cursor = conn.cursor()
    cursor.execute('''
        SELECT tag, COUNT(*) as count
        FROM project_tags
        GROUP BY tag
        ORDER BY count DESC, tag ASC
    ''')

    tags = []
    for row in cursor.fetchall():
        tags.append(dict(row))

    return tags

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected")
    emit('connection_response', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected")

if __name__ == '__main__':
    # Check if database exists
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found: {DB_PATH}")
        print(f"❌ Database not found: {DB_PATH}")
        print("\n💡 The database will be created automatically when you:")
        print("   1. Create your first project: recall <project> --create")
        print("   2. Or run auto-analysis: recall <project> --analyze")
        print(f"\n📁 Expected location: {DB_PATH}")
        print("   Run 'recall --help' for more information\n")
        import sys
        sys.exit(1)

    logger.info(f"Starting Recall Dashboard on {DEFAULT_HOST}:{DEFAULT_PORT}")
    logger.info(f"Live updates enabled via WebSocket")
    logger.info(f"Database: {DB_PATH}")

    print("🧠 Starting Recall Dashboard...")
    print(f"   📊 Dashboard running at: http://{DEFAULT_HOST}:{DEFAULT_PORT}")
    print(f"   ⚡ Live updates enabled (WebSocket)")
    print(f"   🔄 Auto-detects changes every 2 seconds")
    print(f"\n💡 Open http://{DEFAULT_HOST}:{DEFAULT_PORT} in your browser")
    print("   Press Ctrl+C to stop\n")

    # Start background thread for monitoring changes
    monitor_thread = threading.Thread(target=monitor_changes, daemon=True)
    monitor_thread.start()

    # NOTE: Using Werkzeug for local development only. For production deployment, use:
    # gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 dashboard_app:app
    socketio.run(app, host=DEFAULT_HOST, port=DEFAULT_PORT, debug=False, allow_unsafe_werkzeug=True)
