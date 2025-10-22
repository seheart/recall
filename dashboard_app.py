#!/usr/bin/env python3
"""
Recall Dashboard - Flask Web App
Serves the dashboard dynamically with fresh data on every page load
"""
from flask import Flask, render_template, g
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

# Import version
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from recall_lib.__version__ import __version__

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Security Configuration
import secrets
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    logger.warning("⚠️  Using auto-generated SECRET_KEY. Set FLASK_SECRET_KEY environment variable for production.")
app.config['SECRET_KEY'] = SECRET_KEY

# Disable template and static file caching for development
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Make CORS origins configurable via environment variable
ALLOWED_ORIGINS = os.environ.get(
    'RECALL_ALLOWED_ORIGINS',
    'http://127.0.0.1:5000,http://localhost:5000'
).split(',')

# Restrict WebSocket CORS to localhost only for security
socketio = SocketIO(
    app,
    cors_allowed_origins=ALLOWED_ORIGINS,
    async_mode='threading',
    ping_timeout=60,
    ping_interval=25
)

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
    # Length validation (minimum 2 chars, maximum 100)
    if not name or len(name) < 2 or len(name) > 100:
        return False

    # Must start with alphanumeric, then alphanumeric, underscore, or hyphen
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', name):
        return False

    # Prevent directory traversal attempts
    if '..' in name or '/' in name or '\\' in name:
        return False

    # Prevent SQL keywords (defense in depth)
    sql_keywords = {'SELECT', 'DROP', 'DELETE', 'INSERT', 'UPDATE', 'WHERE', 'TABLE', 'FROM'}
    if name.upper() in sql_keywords:
        return False

    return True

# Simple in-memory rate limiter (no external dependencies)
from collections import defaultdict
from functools import wraps
from flask import request, jsonify

_rate_limit_storage = defaultdict(lambda: {'count': 0, 'reset_time': 0})
_rate_limit_lock = threading.Lock()

def rate_limit(max_requests: int = 50, window_seconds: int = 60):
    """
    Simple rate limiting decorator - limits requests per IP address

    Args:
        max_requests: Maximum number of requests allowed in the time window
        window_seconds: Time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get client IP
            client_ip = request.remote_addr or 'unknown'
            current_time = time.time()

            with _rate_limit_lock:
                client_data = _rate_limit_storage[client_ip]

                # Reset if window expired
                if current_time > client_data['reset_time']:
                    client_data['count'] = 0
                    client_data['reset_time'] = current_time + window_seconds

                # Check limit
                if client_data['count'] >= max_requests:
                    retry_after = int(client_data['reset_time'] - current_time)
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'retry_after': retry_after
                    }), 429

                # Increment counter
                client_data['count'] += 1

            return f(*args, **kwargs)
        return wrapped
    return decorator

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

        # Fetch all context items for all projects
        context_cursor = db.execute('''
            SELECT project_id, key, value
            FROM project_context
            ORDER BY project_id
        ''')

        # Group context by project_id
        context_by_project = {}
        for row in context_cursor.fetchall():
            project_id = row['project_id']
            if project_id not in context_by_project:
                context_by_project[project_id] = {}
            context_by_project[project_id][row['key']] = row['value']

        # Add context_data to each project as JSON string
        for project in projects:
            project_id = project['id']
            if project_id in context_by_project:
                project['context_data'] = json.dumps(context_by_project[project_id])
            else:
                project['context_data'] = None

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

@app.after_request
def add_cache_headers(response):
    """Add caching headers to improve performance"""
    response.cache_control.max_age = CACHE_MAX_AGE
    return response

@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Content Security Policy for dashboard
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.socket.io https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self' ws://127.0.0.1:* ws://localhost:* http://127.0.0.1:* http://localhost:*"
    )
    return response

@app.route('/api/recent-activity')
@rate_limit(max_requests=100, window_seconds=60)
def get_recent_activity():
    """API endpoint to fetch recent activity across all projects with filtering and stats"""
    try:
        from datetime import datetime, timedelta
        import re

        db = get_db()

        # Get filter parameters
        project_filter = request.args.get('project', 'all')
        days_filter = int(request.args.get('days', 30))

        # Build query with filters
        query = '''
            SELECT s.summary, s.accomplishments, s.decisions_made, s.next_steps,
                   datetime(s.created_at, 'localtime') as created_at,
                   p.name as project_name,
                   s.files_changed
            FROM sessions s
            JOIN projects p ON s.project_id = p.id
            WHERE datetime(s.created_at) >= datetime('now', '-{} days')
        '''.format(days_filter)

        params = []
        if project_filter != 'all':
            query += ' AND p.name = ?'
            params.append(project_filter)

        query += ' ORDER BY s.created_at DESC LIMIT 50'

        sessions_cursor = db.execute(query, params)
        sessions = [dict(row) for row in sessions_cursor.fetchall()]

        # Detect session type based on summary content
        for session in sessions:
            summary = session.get('summary', '')
            if 'wrap session' in summary.lower() or 'v1.2' in summary:
                session['type'] = 'wrap'
                session['type_icon'] = '🤖'
                session['type_label'] = 'Wrap'
            elif 'commit' in summary.lower() or 'git' in summary.lower():
                session['type'] = 'git'
                session['type_icon'] = '📚'
                session['type_label'] = 'Git'
            elif 'imported from' in session.get('accomplishments', '').lower():
                session['type'] = 'ingest'
                session['type_icon'] = '📝'
                session['type_label'] = 'Markdown'
            else:
                session['type'] = 'manual'
                session['type_icon'] = '✍️'
                session['type_label'] = 'Manual'

        # Calculate stats
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())

        # Sessions today
        sessions_today = sum(1 for s in sessions
                           if datetime.fromisoformat(s['created_at']) >= today_start)

        # Sessions this week
        sessions_week = sum(1 for s in sessions
                          if datetime.fromisoformat(s['created_at']) >= week_start)

        # Calculate streak (consecutive days with activity)
        all_sessions_cursor = db.execute('''
            SELECT DISTINCT date(created_at, 'localtime') as session_date
            FROM sessions
            ORDER BY session_date DESC
        ''')
        session_dates = [row[0] for row in all_sessions_cursor.fetchall()]

        streak = 0
        current_date = now.date()
        for date_str in session_dates:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            if date_obj == current_date or (current_date - date_obj).days == streak:
                streak += 1
                current_date = date_obj
            else:
                break

        # Get list of all projects for filter
        projects_cursor = db.execute('SELECT DISTINCT name FROM projects ORDER BY name')
        all_projects = [row[0] for row in projects_cursor.fetchall()]

        # Get active projects count (projects with sessions in last 7 days)
        active_projects_cursor = db.execute('''
            SELECT COUNT(DISTINCT p.id)
            FROM projects p
            JOIN sessions s ON p.id = s.project_id
            WHERE datetime(s.created_at) >= datetime('now', '-7 days')
        ''')
        active_projects = active_projects_cursor.fetchone()[0]

        return {
            'sessions': sessions,
            'stats': {
                'today': sessions_today,
                'week': sessions_week,
                'streak': streak,
                'active_projects': active_projects
            },
            'filters': {
                'projects': all_projects
            }
        }
    except Exception as e:
        logger.error(f"Error fetching recent activity: {e}")
        return {'error': str(e)}, 500

@app.route('/api/project/<project_name>')
@rate_limit(max_requests=100, window_seconds=60)
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
@rate_limit(max_requests=50, window_seconds=60)  # Lower limit for expensive operation
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

@app.route('/api/insights')
@rate_limit(max_requests=20, window_seconds=60)
def get_insights():
    """API endpoint for enhanced cross-project insights"""
    try:
        db = get_db()

        # Get all projects with their context
        projects = db.execute('''
            SELECT p.id, p.name, p.description, p.directory,
                   datetime(p.created_at, 'localtime') as created_at,
                   datetime(p.updated_at, 'localtime') as updated_at,
                   (SELECT COUNT(*) FROM sessions s WHERE s.project_id = p.id) as session_count,
                   (SELECT COUNT(*) FROM project_context c WHERE c.project_id = p.id) as context_count,
                   GROUP_CONCAT(DISTINCT t.tag) as tags
            FROM projects p
            LEFT JOIN project_tags t ON p.id = t.project_id
            GROUP BY p.id
            ORDER BY p.updated_at DESC
        ''').fetchall()

        projects_list = [dict(row) for row in projects]

        # Aggregate enhanced context data
        tech_stack = {}
        architecture_patterns = {}
        external_integrations = {}
        workflows_count = 0
        health_metrics = {'ci_cd': 0, 'tests': 0, 'linting': 0}
        entry_points_count = 0
        hot_files_count = 0
        known_issues_count = 0

        for project in projects_list:
            # Get context for this project
            context_rows = db.execute('''
                SELECT category, key, value FROM project_context
                WHERE project_id = ?
            ''', (project['id'],)).fetchall()

            for row in context_rows:
                category, key, value = row['category'], row['key'], row['value']

                # Count architecture patterns
                if key == 'architecture_patterns' and value:
                    for pattern in value.split(', '):
                        architecture_patterns[pattern] = architecture_patterns.get(pattern, 0) + 1

                # Count external integrations
                elif key == 'external_integrations' and value:
                    for integration in value.split(', '):
                        external_integrations[integration] = external_integrations.get(integration, 0) + 1

                # Count tech stack
                elif key == 'tech_stack' and value:
                    for tech in value.split(' + '):
                        # Extract just the framework name (e.g., "React" from "React ^18.0.0")
                        tech_name = tech.split()[0]
                        tech_stack[tech_name] = tech_stack.get(tech_name, 0) + 1

                # Count workflows
                elif key == 'workflows' and value:
                    workflows_count += len(value.split(' | '))

                # Count health metrics
                elif key == 'health_metrics' and value:
                    if 'CI/CD' in value:
                        health_metrics['ci_cd'] += 1
                    if 'Tests' in value or 'testing' in value.lower():
                        health_metrics['tests'] += 1
                    if 'Linting' in value or 'linting' in value.lower():
                        health_metrics['linting'] += 1

                # Count entry points
                elif key == 'entry_points' and value:
                    entry_points_count += len(value.split(', '))

                # Count hot files
                elif key == 'hot_files' and value:
                    hot_files_count += len(value.split(', '))

                # Count known issues
                elif key == 'known_issues' and value:
                    known_issues_count += len(value.split(' | '))

        # Activity breakdown
        now = datetime.now()
        active_projects = 0
        idle_projects = 0
        stale_projects = 0

        for project in projects_list:
            if project['updated_at']:
                updated = datetime.fromisoformat(project['updated_at'].replace(' ', 'T'))
                days_ago = (now - updated).days
                if days_ago <= 7:
                    active_projects += 1
                elif days_ago <= 30:
                    idle_projects += 1
                else:
                    stale_projects += 1

        # Sort and limit top items
        top_tech_stack = sorted(tech_stack.items(), key=lambda x: x[1], reverse=True)[:10]
        top_architecture = sorted(architecture_patterns.items(), key=lambda x: x[1], reverse=True)[:8]
        top_integrations = sorted(external_integrations.items(), key=lambda x: x[1], reverse=True)[:10]

        # Calculate totals
        total_projects = len(projects_list)
        total_sessions = sum(p['session_count'] for p in projects_list)
        total_context = sum(p['context_count'] for p in projects_list)

        return {
            'overview': {
                'total_projects': total_projects,
                'total_sessions': total_sessions,
                'total_context': total_context,
                'avg_sessions': round(total_sessions / total_projects, 1) if total_projects > 0 else 0,
                'avg_context': round(total_context / total_projects, 1) if total_projects > 0 else 0,
            },
            'activity': {
                'active': active_projects,
                'idle': idle_projects,
                'stale': stale_projects,
            },
            'tech_stack': top_tech_stack,
            'architecture_patterns': top_architecture,
            'external_integrations': top_integrations,
            'workflows_count': workflows_count,
            'entry_points_count': entry_points_count,
            'hot_files_count': hot_files_count,
            'known_issues_count': known_issues_count,
            'health_metrics': health_metrics,
            'most_active': [{'name': p['name'], 'sessions': p['session_count']}
                           for p in sorted(projects_list, key=lambda x: x['session_count'], reverse=True)[:5]],
            'most_documented': [{'name': p['name'], 'context': p['context_count']}
                               for p in sorted(projects_list, key=lambda x: x['context_count'], reverse=True)[:5]],
        }

    except Exception as e:
        logger.error(f"Error fetching insights: {e}")
        return {'error': str(e)}, 500

@app.route('/')
def dashboard():
    """Serve the dashboard with fresh data"""
    projects = get_projects_data()
    tags = get_tags_data()
    # Note: No longer loading all project details upfront (lazy loading)

    return render_template(
        'dashboard.html',
        projects_json=json.dumps(projects),
        tags_json=json.dumps(tags),
        auto_refresh_ms=AUTO_REFRESH_INTERVAL_MS,
        search_debounce_ms=SEARCH_DEBOUNCE_MS,
        max_cache_size=MAX_PROJECT_CACHE_SIZE,
        version=__version__
    )

# Global variable to store data hash for change detection
_last_data_hash = None
_hash_lock = threading.Lock()

def get_data_hash() -> str:
    """Get hash of current project data for change detection (SHA256)"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            projects = get_projects_data_direct(conn)
            # Create hash of project data using SHA256
            data_str = json.dumps(projects, sort_keys=True)
            return hashlib.sha256(data_str.encode()).hexdigest()
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
            datetime(p.created_at, 'localtime') as created_at,
            datetime(p.updated_at, 'localtime') as updated_at,
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

    # Fetch all context items for all projects
    context_cursor = conn.cursor()
    context_cursor.execute('''
        SELECT project_id, key, value
        FROM project_context
        ORDER BY project_id
    ''')

    # Group context by project_id
    context_by_project = {}
    for row in context_cursor.fetchall():
        project_id = row[0]  # Using index since we may not have row_factory
        key = row[1]
        value = row[2]
        if project_id not in context_by_project:
            context_by_project[project_id] = {}
        context_by_project[project_id][key] = value

    # Add context_data to each project as JSON string
    for project in projects:
        project_id = project['id']
        if project_id in context_by_project:
            project['context_data'] = json.dumps(context_by_project[project_id])
        else:
            project['context_data'] = None

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
    print(f"   ⚡️ Live updates enabled (WebSocket)")
    print(f"   🔄 Auto-detects changes every 2 seconds")
    print(f"\n💡 Open http://{DEFAULT_HOST}:{DEFAULT_PORT} in your browser")
    print("   Press Ctrl+C to stop\n")

    # Start background thread for monitoring changes
    monitor_thread = threading.Thread(target=monitor_changes, daemon=True)
    monitor_thread.start()

    # Auto-open browser after a short delay
    def open_browser():
        time.sleep(1.5)  # Wait for server to start
        import subprocess
        try:
            subprocess.run(['xdg-open', f'http://{DEFAULT_HOST}:{DEFAULT_PORT}'], check=False)
        except Exception as e:
            logger.debug(f"Could not auto-open browser: {e}")

    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    # NOTE: Using Werkzeug for local development only. For production deployment, use:
    # gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 dashboard_app:app
    socketio.run(app, host=DEFAULT_HOST, port=DEFAULT_PORT, debug=False, allow_unsafe_werkzeug=True)
