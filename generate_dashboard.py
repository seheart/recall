#!/usr/bin/env python3
"""
Generate Recall Dashboard HTML
Queries the database and creates a beautiful HTML dashboard
"""
import sqlite3
import json
import os
from pathlib import Path

# Database path
DB_PATH = os.path.join(os.path.expanduser("~"), ".local", "share", "recall", "projects.db")
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")


def get_projects_data():
    """Get all projects with their stats"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute(
        """
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
    """
    )

    projects = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return projects


def get_tags_data():
    """Get all tags with counts"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cursor = conn.execute(
        """
        SELECT
            tag,
            COUNT(*) as count
        FROM project_tags
        GROUP BY tag
        ORDER BY tag ASC
    """
    )

    tags = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tags


def get_project_details():
    """Get full details for all projects including context and sessions"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get all projects
    cursor = conn.execute("SELECT id, name FROM projects")
    projects = cursor.fetchall()

    details = {}
    for project in projects:
        project_id = project["id"]
        project_name = project["name"]

        # Get context organized by category
        context_cursor = conn.execute(
            """
            SELECT category, key, value
            FROM project_context
            WHERE project_id = ?
            ORDER BY category, key
        """,
            (project_id,),
        )

        context = {}
        for row in context_cursor.fetchall():
            category = row["category"]
            if category not in context:
                context[category] = []
            context[category].append({"key": row["key"], "value": row["value"]})

        # Get recent sessions
        sessions_cursor = conn.execute(
            """
            SELECT
                summary,
                accomplishments,
                decisions_made,
                next_steps,
                datetime(created_at, 'localtime') as created_at
            FROM sessions
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT 3
        """,
            (project_id,),
        )

        sessions = [dict(row) for row in sessions_cursor.fetchall()]

        details[project_name] = {"context": context, "sessions": sessions}

    conn.close()
    return details


def generate_html(projects, tags, details):
    """Generate the HTML dashboard with Tokyo Night theme"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recall Dashboard - Project Memory System</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='0.9em' font-size='90'>🧠</text></svg>">
    <style>
        /* Default Theme Variables */
        :root {{
            --radius: 4px;
            --mono: "JetBrains Mono", "Fira Code", "Hack Nerd Font", ui-monospace, monospace;
        }}

        /* Gruvbox Light Theme */
        body.theme--day {{
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
        }}

        /* Ristretto Theme */
        body.theme--dusk {{
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
        }}

        /* Tokyo Night Theme */
        body.theme--night {{
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
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: var(--mono);
            background: var(--bg);
            min-height: 100vh;
            padding: 12px;
            color: var(--text);
            font-size: 12px;
            line-height: 1.4;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}

        .topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            margin-bottom: 12px;
        }}

        .brand {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 700;
            font-size: 13px;
            color: var(--text-heading);
        }}

        .brand::before {{
            content: "🧠";
            font-size: 16px;
        }}

        .theme-switch {{
            display: flex;
            gap: 6px;
        }}

        .theme-btn {{
            padding: 4px 10px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--text);
            cursor: pointer;
            font-family: var(--mono);
            font-size: 11px;
            transition: all 0.2s;
        }}

        .theme-btn:hover {{
            background: var(--surface-2);
            border-color: var(--accent);
        }}

        .theme-btn.active {{
            background: var(--accent);
            color: var(--bg);
            border-color: var(--accent);
        }}

        header {{
            background: var(--surface);
            padding: 16px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            margin-bottom: 12px;
        }}

        h1 {{
            font-size: 14px;
            color: var(--text-heading);
            margin-bottom: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}

        .subtitle {{
            color: var(--muted);
            font-size: 11px;
            margin-bottom: 12px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 8px;
            margin-top: 12px;
        }}

        .stat-card {{
            background: var(--surface-2);
            padding: 10px 12px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            text-align: center;
        }}

        .stat-number {{
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 3px;
            color: var(--accent);
        }}

        .stat-label {{
            font-size: 10px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .controls {{
            background: var(--surface);
            padding: 10px 12px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            margin-bottom: 12px;
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
        }}

        .search-box {{
            flex: 1;
            min-width: 200px;
        }}

        .search-box input {{
            width: 100%;
            padding: 6px 10px;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            font-size: 12px;
            transition: border-color 0.2s;
            background: var(--surface-2);
            color: var(--text);
            font-family: var(--mono);
        }}

        .search-box input::placeholder {{
            color: var(--muted);
        }}

        .search-box input:focus {{
            outline: none;
            border-color: var(--accent);
        }}

        .tag-filters {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }}

        .tag-filter {{
            padding: 4px 10px;
            background: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            cursor: pointer;
            transition: all 0.2s;
            font-size: 11px;
            color: var(--text);
        }}

        .tag-filter:hover {{
            background: var(--accent);
            color: var(--bg);
            border-color: var(--accent);
        }}

        .tag-filter.active {{
            background: var(--accent);
            color: var(--bg);
            border-color: var(--accent);
        }}

        .projects-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 8px;
            margin-bottom: 12px;
        }}

        .project-card {{
            background: var(--surface);
            border-radius: var(--radius);
            padding: 12px;
            border: 1px solid var(--border);
            transition: all 0.2s;
            position: relative;
            cursor: pointer;
        }}

        .project-card:hover {{
            border-color: var(--accent);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }}

        .project-card::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 3px;
            height: 100%;
            background: var(--accent);
        }}

        .project-header {{
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 8px;
            padding-left: 8px;
        }}

        .project-name {{
            font-size: 13px;
            font-weight: 700;
            color: var(--text-heading);
            margin-bottom: 3px;
        }}

        .project-description {{
            color: var(--muted);
            margin-bottom: 8px;
            line-height: 1.5;
            font-size: 11px;
            padding-left: 8px;
        }}

        .project-path {{
            color: var(--muted);
            font-size: 10px;
            margin-bottom: 8px;
            word-break: break-all;
            padding-left: 8px;
        }}

        .project-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-bottom: 8px;
            padding-left: 8px;
        }}

        .tag {{
            display: inline-block;
            padding: 2px 6px;
            background: var(--chip-bg);
            color: var(--accent);
            border-radius: var(--radius);
            font-size: 10px;
            font-weight: 500;
            border: 1px solid var(--border);
        }}

        .project-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            padding-top: 8px;
            border-top: 1px solid var(--border);
            padding-left: 8px;
        }}

        .project-stat {{
            text-align: center;
        }}

        .project-stat-number {{
            font-size: 16px;
            font-weight: 700;
            color: var(--accent);
        }}

        .project-stat-label {{
            font-size: 9px;
            color: var(--muted);
            margin-top: 2px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .project-date {{
            font-size: 10px;
            color: var(--muted);
            text-align: right;
            margin-top: 6px;
            padding-left: 8px;
        }}

        .no-results {{
            text-align: center;
            padding: 40px 20px;
            background: var(--surface);
            border-radius: var(--radius);
            border: 1px solid var(--border);
            color: var(--muted);
            font-size: 12px;
        }}

        .no-results::before {{
            content: "🔍";
            display: block;
            font-size: 32px;
            margin-bottom: 12px;
        }}

        /* Tooltip styles */
        .tooltip {{
            position: relative;
            cursor: help;
            border-bottom: 1px dotted var(--muted);
        }}

        .tooltip:hover::after {{
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
            white-space: nowrap;
            font-size: 11px;
            z-index: 1000;
            margin-bottom: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}

        .tooltip:hover::before {{
            content: "";
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            border: 4px solid transparent;
            border-top-color: var(--border);
            z-index: 1001;
        }}

        footer {{
            text-align: center;
            color: var(--muted);
            padding: 16px;
            margin-top: 20px;
            font-size: 11px;
            opacity: 0.8;
            border-top: 1px solid var(--border);
        }}

        footer a {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 600;
            transition: color 0.2s;
        }}

        footer a:hover {{
            color: var(--accent-2);
            text-decoration: underline;
        }}

        /* Modal styles */
        .modal {{
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
        }}

        .modal.active {{
            display: flex;
            align-items: flex-start;
            justify-content: center;
        }}

        .modal-content {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            max-width: 900px;
            width: 100%;
            margin: 40px auto;
            padding: 20px;
            position: relative;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }}

        .modal-close {{
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
        }}

        .modal-close:hover {{
            background: var(--accent);
            color: var(--bg);
            border-color: var(--accent);
        }}

        .modal-header {{
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 16px;
        }}

        .modal-title {{
            font-size: 16px;
            font-weight: 700;
            color: var(--text-heading);
            margin-bottom: 4px;
        }}

        .modal-subtitle {{
            font-size: 11px;
            color: var(--muted);
        }}

        .context-section {{
            margin-bottom: 16px;
        }}

        .context-section-title {{
            font-size: 12px;
            font-weight: 700;
            color: var(--accent);
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .context-items {{
            background: var(--surface-2);
            padding: 10px 12px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
        }}

        .context-item {{
            font-size: 11px;
            padding: 4px 0;
            color: var(--text);
            border-bottom: 1px solid var(--border);
        }}

        .context-item:last-child {{
            border-bottom: none;
        }}

        .context-key {{
            color: var(--accent);
            font-weight: 600;
            margin-right: 8px;
        }}

        .session-card {{
            background: var(--surface-2);
            padding: 10px 12px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            margin-bottom: 8px;
        }}

        .session-date {{
            font-size: 10px;
            color: var(--muted);
            margin-bottom: 6px;
        }}

        .session-detail {{
            font-size: 11px;
            margin-bottom: 4px;
            color: var(--text);
        }}

        .session-label {{
            color: var(--accent);
            font-weight: 600;
        }}

        .no-data {{
            text-align: center;
            padding: 20px;
            color: var(--muted);
            font-size: 11px;
            font-style: italic;
        }}

        .refresh-notice {{
            background: var(--surface-2);
            color: var(--accent);
            padding: 8px 12px;
            border-radius: var(--radius);
            border: 1px solid var(--border);
            margin-bottom: 12px;
            font-size: 11px;
        }}

        .refresh-notice code {{
            background: var(--code-bg);
            color: var(--accent-2);
            padding: 2px 6px;
            border-radius: var(--radius);
            font-family: var(--mono);
            font-size: 10px;
        }}

        @media (max-width: 768px) {{
            .projects-grid {{
                grid-template-columns: 1fr;
            }}

            .controls {{
                flex-direction: column;
                align-items: stretch;
            }}

            .theme-switch {{
                order: -1;
                justify-content: center;
            }}
        }}
    </style>
</head>
<body class="theme--night">
    <div class="container">
        <div class="topbar">
            <div class="brand">RECALL</div>
            <div class="theme-switch">
                <button class="theme-btn" data-theme="day">Gruvbox</button>
                <button class="theme-btn" data-theme="dusk">Ristretto</button>
                <button class="theme-btn active" data-theme="night">Tokyo Night</button>
            </div>
        </div>

        <header>
            <h1>PROJECT MEMORY DASHBOARD</h1>
            <div class="subtitle">Real-time monitoring • Claude Code integration</div>

            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="total-projects">0</div>
                    <div class="stat-label tooltip" data-tooltip="Number of projects tracked in your memory system">Projects</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-sessions">0</div>
                    <div class="stat-label tooltip" data-tooltip="Development sessions logged (what you worked on and when)">Sessions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-context">0</div>
                    <div class="stat-label tooltip" data-tooltip="Pieces of context stored (architecture, decisions, state, etc.)">Context Items</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="total-tags">0</div>
                    <div class="stat-label tooltip" data-tooltip="Tags used to categorize projects (web, api, cli, etc.)">Tags</div>
                </div>
            </div>
        </header>

        <div class="refresh-notice" style="display: flex; justify-content: space-between; align-items: center;">
            <div>💡 Page reloads every 30 seconds • Regenerate data with <code>python3 recall.py --dashboard</code> • Last updated: <span id="last-updated"></span></div>
            <button id="manual-refresh" class="theme-btn" style="background: var(--accent); color: var(--bg); border-color: var(--accent);">🔄 Refresh Page</button>
        </div>

        <div class="controls">
            <div class="search-box">
                <input type="text" id="search" placeholder="🔍 Search projects..." />
            </div>
            <div class="tag-filters" id="tag-filters">
                <!-- Tags will be inserted here -->
            </div>
        </div>

        <div class="projects-grid" id="projects-grid">
            <!-- Project cards will be inserted here -->
        </div>

        <footer>
            Generated by Recall Dashboard • Data from ~/.local/share/recall/projects.db<br>
            <a href="https://github.com/seheart/recall#readme" target="_blank" rel="noopener noreferrer">About</a> •
            <a href="https://github.com/seheart/recall#-quick-start" target="_blank" rel="noopener noreferrer">How to Use</a> •
            Built with love by <a href="https://setheheart.com" target="_blank" rel="noopener noreferrer">Seth Eheart</a> of <a href="https://ant312.com" target="_blank" rel="noopener noreferrer">ANT</a>
        </footer>
    </div>

    <!-- Project Details Modal -->
    <div class="modal" id="project-modal">
        <div class="modal-content">
            <button class="modal-close" onclick="closeModal()">&times;</button>
            <div id="modal-body"></div>
        </div>
    </div>

    <script>
        // Project data from database
        const projectsData = {json.dumps(projects)};
        const tagsData = {json.dumps(tags)};
        const projectDetails = {json.dumps(details)};

        let currentFilter = null;
        let currentSearch = '';

        // Theme switcher
        const themeButtons = document.querySelectorAll('.theme-btn');
        themeButtons.forEach(btn => {{
            btn.addEventListener('click', () => {{
                const theme = btn.dataset.theme;
                document.body.className = `theme--${{theme}}`;

                // Update active state
                themeButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Save preference
                localStorage.setItem('recall-theme', theme);
            }});
        }});

        // Load saved theme
        const savedTheme = localStorage.getItem('recall-theme');
        if (savedTheme) {{
            document.body.className = `theme--${{savedTheme}}`;
            themeButtons.forEach(btn => {{
                btn.classList.toggle('active', btn.dataset.theme === savedTheme);
            }});
        }}

        // Calculate statistics
        function updateStats() {{
            const totalProjects = projectsData.length;
            const totalSessions = projectsData.reduce((sum, p) => sum + p.session_count, 0);
            const totalContext = projectsData.reduce((sum, p) => sum + p.context_count, 0);
            const totalTags = tagsData.length;

            document.getElementById('total-projects').textContent = totalProjects;
            document.getElementById('total-sessions').textContent = totalSessions;
            document.getElementById('total-context').textContent = totalContext;
            document.getElementById('total-tags').textContent = totalTags;
        }}

        // Render tag filters
        function renderTagFilters() {{
            const container = document.getElementById('tag-filters');
            container.innerHTML = '<div class="tag-filter active" data-tag="all">All Projects</div>';

            tagsData.forEach(tagData => {{
                const tagEl = document.createElement('div');
                tagEl.className = 'tag-filter';
                tagEl.dataset.tag = tagData.tag;
                tagEl.textContent = `${{tagData.tag}} (${{tagData.count}})`;
                tagEl.addEventListener('click', () => filterByTag(tagData.tag));
                container.appendChild(tagEl);
            }});

            // Add "all" filter
            container.firstChild.addEventListener('click', () => filterByTag(null));
        }}

        // Filter by tag
        function filterByTag(tag) {{
            currentFilter = tag;
            document.querySelectorAll('.tag-filter').forEach(el => {{
                el.classList.remove('active');
                if ((tag === null && el.dataset.tag === 'all') || el.dataset.tag === tag) {{
                    el.classList.add('active');
                }}
            }});
            renderProjects();
        }}

        // Search projects
        document.getElementById('search').addEventListener('input', (e) => {{
            currentSearch = e.target.value.toLowerCase();
            renderProjects();
        }});

        // Render projects
        function renderProjects() {{
            const container = document.getElementById('projects-grid');
            const filtered = projectsData.filter(project => {{
                // Filter by tag
                if (currentFilter) {{
                    const projectTags = project.tags ? project.tags.split(',') : [];
                    if (!projectTags.includes(currentFilter)) return false;
                }}

                // Filter by search
                if (currentSearch) {{
                    const searchable = `${{project.name}} ${{project.description || ''}} ${{project.tags || ''}}`.toLowerCase();
                    if (!searchable.includes(currentSearch)) return false;
                }}

                return true;
            }});

            if (filtered.length === 0) {{
                container.innerHTML = '<div class="no-results">No projects found</div>';
                return;
            }}

            container.innerHTML = filtered.map(project => {{
                const tags = project.tags ? project.tags.split(',').map(tag =>
                    `<span class="tag">${{tag}}</span>`
                ).join('') : '<span style="color: #999; font-size: 0.85em;">No tags</span>';

                const description = project.description
                    ? `<div class="project-description">${{project.description}}</div>`
                    : '';

                return `
                    <div class="project-card" onclick="showProjectDetails('${{project.name}}')">
                        <div class="project-header">
                            <div>
                                <div class="project-name">${{project.name}}</div>
                            </div>
                        </div>
                        ${{description}}
                        <div class="project-path">📁 ${{project.directory}}</div>
                        <div class="project-tags">${{tags}}</div>
                        <div class="project-stats">
                            <div class="project-stat">
                                <div class="project-stat-number">${{project.session_count}}</div>
                                <div class="project-stat-label tooltip" data-tooltip="Development sessions logged">Sessions</div>
                            </div>
                            <div class="project-stat">
                                <div class="project-stat-number">${{project.context_count}}</div>
                                <div class="project-stat-label tooltip" data-tooltip="Context items (architecture, decisions, state)">Context</div>
                            </div>
                            <div class="project-stat">
                                <div class="project-stat-number">${{project.tags ? project.tags.split(',').length : 0}}</div>
                                <div class="project-stat-label tooltip" data-tooltip="Category tags for this project">Tags</div>
                            </div>
                        </div>
                        <div class="project-date">
                            Updated: ${{new Date(project.updated_at).toLocaleString()}}
                        </div>
                    </div>
                `;
            }}).join('');
        }}

        // Modal functions
        function showProjectDetails(projectName) {{
            const project = projectsData.find(p => p.name === projectName);
            const details = projectDetails[projectName];

            if (!project || !details) {{
                return;
            }}

            let html = `
                <div class="modal-header">
                    <div class="modal-title">${{project.name.toUpperCase()}}</div>
                    <div class="modal-subtitle">${{project.description || 'No description'}}</div>
                    <div class="modal-subtitle">📁 ${{project.directory}}</div>
                    <div class="modal-subtitle">Updated: ${{project.updated_at}}</div>
                </div>
            `;

            // Add context sections
            const contextCategories = Object.keys(details.context);
            if (contextCategories.length > 0) {{
                contextCategories.forEach(category => {{
                    const categoryName = category.replace(/_/g, ' ').toUpperCase();
                    const icon = getCategoryIcon(category);
                    html += `
                        <div class="context-section">
                            <div class="context-section-title">${{icon}} ${{categoryName}}</div>
                            <div class="context-items">
                    `;

                    details.context[category].forEach(item => {{
                        const key = item.key.replace(/_/g, ' ');
                        html += `<div class="context-item"><span class="context-key">${{key}}:</span>${{item.value}}</div>`;
                    }});

                    html += `
                            </div>
                        </div>
                    `;
                }});
            }} else {{
                html += '<div class="no-data">No context data available. Run <code>recall ${{projectName}} --analyze</code> to populate.</div>';
            }}

            // Add sessions
            if (details.sessions && details.sessions.length > 0) {{
                html += '<div class="context-section"><div class="context-section-title">📝 RECENT SESSIONS</div>';

                details.sessions.forEach((session, index) => {{
                    html += `
                        <div class="session-card">
                            <div class="session-date">Session ${{index + 1}} - ${{session.created_at}}</div>
                    `;

                    if (session.summary) {{
                        html += `<div class="session-detail"><span class="session-label">Summary:</span> ${{session.summary}}</div>`;
                    }}
                    if (session.accomplishments) {{
                        html += `<div class="session-detail"><span class="session-label">Accomplishments:</span> ${{session.accomplishments}}</div>`;
                    }}
                    if (session.decisions_made) {{
                        html += `<div class="session-detail"><span class="session-label">Decisions:</span> ${{session.decisions_made}}</div>`;
                    }}
                    if (session.next_steps) {{
                        html += `<div class="session-detail"><span class="session-label">Next Steps:</span> ${{session.next_steps}}</div>`;
                    }}

                    html += '</div>';
                }});

                html += '</div>';
            }} else {{
                html += '<div class="context-section"><div class="context-section-title">📝 RECENT SESSIONS</div><div class="no-data">No sessions logged yet.</div></div>';
            }}

            document.getElementById('modal-body').innerHTML = html;
            document.getElementById('project-modal').classList.add('active');
        }}

        function closeModal() {{
            document.getElementById('project-modal').classList.remove('active');
        }}

        function getCategoryIcon(category) {{
            const icons = {{
                'architecture': '🏗️',
                'state': '⚡️',
                'decisions': '🎯',
                'git': '📦',
                'npm': '📦',
                'structure': '📂',
                'info': 'ℹ️',
                'auto_analyzed': '🔍',
                'environment': '⚙️',
                'documentation': '📄'
            }};
            return icons[category] || '•';
        }}

        // Close modal on background click
        document.getElementById('project-modal').addEventListener('click', (e) => {{
            if (e.target.id === 'project-modal') {{
                closeModal();
            }}
        }});

        // Close modal on Escape key
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                closeModal();
            }}
        }});

        // Auto-refresh every 30 seconds
        let autoRefreshInterval = setInterval(() => {{
            location.reload();
        }}, 30000);

        // Manual refresh button - just reload the page
        document.getElementById('manual-refresh').addEventListener('click', () => {{
            location.reload();
        }});

        // Update last updated time
        document.getElementById('last-updated').textContent = new Date().toLocaleString();

        // Initialize
        updateStats();
        renderTagFilters();
        filterByTag(null); // Show all by default
    </script>
</body>
</html>"""

    return html


def main():
    print("🧠 Generating Recall Dashboard...")

    # Get data
    projects = get_projects_data()
    tags = get_tags_data()
    details = get_project_details()

    print(f"   📊 Found {len(projects)} projects")
    print(f"   🏷️  Found {len(tags)} tags")

    # Generate HTML
    html = generate_html(projects, tags, details)

    # Write to file
    with open(OUTPUT_PATH, "w") as f:
        f.write(html)

    print(f"   ✅ Dashboard generated: {OUTPUT_PATH}")
    print(f"\n💡 Open with: xdg-open {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
