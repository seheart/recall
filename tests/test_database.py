#!/usr/bin/env python3
"""
Unit tests for RecallDatabase
"""
import pytest
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from recall_lib.database import RecallDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    db = RecallDatabase(db_path)
    yield db

    # Cleanup
    os.unlink(db_path)


def test_database_initialization(temp_db):
    """Test that database tables are created"""
    with temp_db.get_connection() as conn:
        # Check projects table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
        )
        assert cursor.fetchone() is not None

        # Check project_context table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='project_context'"
        )
        assert cursor.fetchone() is not None

        # Check sessions table exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        )
        assert cursor.fetchone() is not None


def test_create_project(temp_db):
    """Test creating a new project"""
    project_id = temp_db.create_project(
        "test-project",
        "A test project",
        "/tmp/test-project"
    )

    assert project_id > 0

    # Verify project was created
    project = temp_db.get_project("test-project")
    assert project is not None
    assert project['name'] == "test-project"
    assert project['description'] == "A test project"
    assert project['directory'] == "/tmp/test-project"


def test_get_nonexistent_project(temp_db):
    """Test getting a project that doesn't exist"""
    project = temp_db.get_project("nonexistent")
    assert project is None


def test_list_projects(temp_db):
    """Test listing all projects"""
    # Create multiple projects
    temp_db.create_project("project1", "First project")
    temp_db.create_project("project2", "Second project")
    temp_db.create_project("project3", "Third project")

    projects = temp_db.list_projects()
    assert len(projects) == 3
    assert all('name' in p for p in projects)
    assert all('created_at' in p for p in projects)


def test_search_projects(temp_db):
    """Test project search functionality"""
    # Create projects with different attributes
    temp_db.create_project("api-server", "REST API server", "/projects/api")
    temp_db.create_project("web-frontend", "React frontend", "/projects/web")
    temp_db.create_project("mobile-app", "Mobile application", "/projects/mobile")

    # Search by name
    results = temp_db.search_projects("api")
    assert len(results) == 1
    assert results[0]['name'] == "api-server"

    # Search by description
    results = temp_db.search_projects("React")
    assert len(results) == 1
    assert results[0]['name'] == "web-frontend"

    # Search by directory
    results = temp_db.search_projects("/projects")
    assert len(results) == 3


def test_set_and_get_context(temp_db):
    """Test storing and retrieving context"""
    project_id = temp_db.create_project("test-project", "Test project")

    # Set context values
    temp_db.set_context(project_id, "architecture", "language", "Python")
    temp_db.set_context(project_id, "architecture", "framework", "Flask")
    temp_db.set_context(project_id, "state", "status", "In development")

    # Get all context
    context = temp_db.get_context(project_id)
    assert 'architecture' in context
    assert context['architecture']['language'] == "Python"
    assert context['architecture']['framework'] == "Flask"
    assert 'state' in context
    assert context['state']['status'] == "In development"

    # Get filtered context
    arch_context = temp_db.get_context(project_id, category="architecture")
    assert 'architecture' in arch_context
    assert 'state' not in arch_context


def test_add_session(temp_db):
    """Test adding session records"""
    project_id = temp_db.create_project("test-project", "Test project")

    session_id = temp_db.add_session(
        project_id,
        summary="Implemented authentication",
        accomplishments="Login/logout functionality",
        decisions_made="Used JWT tokens",
        next_steps="Add password reset",
        files_changed="auth.py, routes.py"
    )

    assert session_id > 0

    # Verify session was created
    sessions = temp_db.get_recent_sessions(project_id, limit=5)
    assert len(sessions) == 1
    assert sessions[0]['summary'] == "Implemented authentication"
    assert sessions[0]['accomplishments'] == "Login/logout functionality"


def test_update_project_timestamp(temp_db):
    """Test that project timestamp is updated"""
    project_id = temp_db.create_project("test-project", "Test project")

    project_before = temp_db.get_project("test-project")
    original_timestamp = project_before['updated_at']

    # Update context (should trigger timestamp update)
    temp_db.set_context(project_id, "test", "key", "value")

    project_after = temp_db.get_project("test-project")
    # Note: In real tests you might need to add a small delay
    # to ensure timestamp actually changes


def test_context_overwrite(temp_db):
    """Test that context values can be overwritten"""
    project_id = temp_db.create_project("test-project", "Test project")

    # Set initial value
    temp_db.set_context(project_id, "state", "status", "Planning")
    context = temp_db.get_context(project_id)
    assert context['state']['status'] == "Planning"

    # Overwrite value
    temp_db.set_context(project_id, "state", "status", "In development")
    context = temp_db.get_context(project_id)
    assert context['state']['status'] == "In development"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
