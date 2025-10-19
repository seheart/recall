#!/usr/bin/env python3
"""
Unit tests for ProjectMemory with caching
"""
import pytest
import tempfile
import os
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from recall_lib.project_memory import ProjectMemory


@pytest.fixture
def temp_memory():
    """Create a temporary ProjectMemory instance"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name

    memory = ProjectMemory(db_path)
    yield memory

    # Cleanup
    os.unlink(db_path)


def test_create_project(temp_memory):
    """Test creating a new project"""
    project_id = temp_memory.create_project(
        "test-app",
        "A test application",
        "/tmp/test-app"
    )

    assert project_id > 0
    assert temp_memory.project_exists("test-app")


def test_create_project_with_initial_context(temp_memory):
    """Test creating a project with initial context"""
    initial_context = {
        "architecture": {
            "language": "Python",
            "framework": "Flask"
        },
        "state": {
            "status": "Planning"
        }
    }

    project_id = temp_memory.create_project(
        "test-app",
        "A test application",
        initial_context=initial_context
    )

    # Verify context was set
    context = temp_memory.get_project_context("test-app")
    assert context is not None
    assert 'architecture' in context['context']
    assert context['context']['architecture']['language'] == "Python"


def test_get_project_context_caching(temp_memory):
    """Test that project context is cached"""
    temp_memory.create_project("test-app", "A test application")

    # First call - should hit database
    context1 = temp_memory.get_project_context("test-app")
    assert context1 is not None

    # Check cache was populated
    assert "test-app" in temp_memory._context_cache

    # Second call - should hit cache
    context2 = temp_memory.get_project_context("test-app")
    assert context2 is not None

    # Should be the same object (from cache)
    assert context1 == context2


def test_cache_invalidation_on_update(temp_memory):
    """Test that cache is invalidated when project is updated"""
    temp_memory.create_project("test-app", "A test application")

    # Load into cache
    context1 = temp_memory.get_project_context("test-app")
    assert "test-app" in temp_memory._context_cache

    # Update architecture
    temp_memory.update_architecture("test-app", {"language": "Go"})

    # Cache should be invalidated
    assert "test-app" not in temp_memory._context_cache


def test_cache_ttl_expiration(temp_memory):
    """Test that cache expires after TTL"""
    # Set a very short TTL for testing
    temp_memory.CACHE_TTL = 1  # 1 second

    temp_memory.create_project("test-app", "A test application")

    # Load into cache
    temp_memory.get_project_context("test-app")
    assert "test-app" in temp_memory._context_cache

    # Wait for TTL to expire
    time.sleep(1.5)

    # Next call should clear expired cache and reload
    temp_memory.get_project_context("test-app")
    # Cache should be repopulated
    assert "test-app" in temp_memory._context_cache


def test_update_architecture(temp_memory):
    """Test updating project architecture"""
    temp_memory.create_project("test-app", "A test application")

    arch_data = {
        "language": "Python",
        "framework": "Django",
        "database": "PostgreSQL"
    }

    temp_memory.update_architecture("test-app", arch_data)

    context = temp_memory.get_project_context("test-app")
    assert 'architecture' in context['context']
    assert context['context']['architecture']['language'] == "Python"
    assert context['context']['architecture']['framework'] == "Django"


def test_update_state(temp_memory):
    """Test updating project state"""
    temp_memory.create_project("test-app", "A test application")

    state_data = {
        "status": "In development",
        "current_feature": "User authentication"
    }

    temp_memory.update_state("test-app", state_data)

    context = temp_memory.get_project_context("test-app")
    assert 'state' in context['context']
    assert context['context']['state']['status'] == "In development"


def test_record_decision(temp_memory):
    """Test recording technical decisions"""
    temp_memory.create_project("test-app", "A test application")

    temp_memory.record_decision(
        "test-app",
        "database",
        "PostgreSQL",
        "Needed ACID compliance and complex queries"
    )

    context = temp_memory.get_project_context("test-app")
    assert 'decisions' in context['context']
    assert context['context']['decisions']['database'] == "PostgreSQL"
    assert 'reasoning' in context['context']
    assert context['context']['reasoning']['database'] == "Needed ACID compliance and complex queries"


def test_log_session(temp_memory):
    """Test logging development sessions"""
    temp_memory.create_project("test-app", "A test application")

    session_id = temp_memory.log_session(
        "test-app",
        summary="Implemented user authentication",
        accomplishments=["Login page", "Logout functionality", "Password hashing"],
        next_steps=["Password reset", "Email verification"]
    )

    assert session_id > 0

    context = temp_memory.get_project_context("test-app")
    assert len(context['recent_sessions']) > 0
    assert context['recent_sessions'][0]['summary'] == "Implemented user authentication"


def test_list_all_projects(temp_memory):
    """Test listing all projects"""
    temp_memory.create_project("app1", "First app")
    temp_memory.create_project("app2", "Second app")
    temp_memory.create_project("app3", "Third app")

    projects = temp_memory.list_all_projects()
    assert len(projects) == 3


def test_search_projects(temp_memory):
    """Test project search"""
    temp_memory.create_project("api-server", "REST API", "/projects/api")
    temp_memory.create_project("frontend", "React app", "/projects/web")

    results = temp_memory.search_projects("api")
    assert len(results) == 1
    assert results[0]['name'] == "api-server"


def test_format_for_claude(temp_memory):
    """Test formatting project context for Claude Code"""
    temp_memory.create_project("test-app", "A test application")
    temp_memory.update_architecture("test-app", {"language": "Python"})

    formatted = temp_memory.format_for_claude("test-app")

    assert "PROJECT MEMORY LOADED" in formatted
    assert "test-app" in formatted.upper()
    assert "ARCHITECTURE" in formatted
    assert "Python" in formatted


def test_nonexistent_project(temp_memory):
    """Test operations on nonexistent project"""
    context = temp_memory.get_project_context("nonexistent")
    assert context is None

    assert not temp_memory.project_exists("nonexistent")

    with pytest.raises(ValueError):
        temp_memory.update_architecture("nonexistent", {"test": "value"})


def test_cache_size_limit(temp_memory):
    """Test that cache enforces size limit"""
    # Set a small cache size
    temp_memory.MAX_CACHE_SIZE = 3

    # Create and access more projects than cache can hold
    for i in range(5):
        temp_memory.create_project(f"app{i}", f"App {i}")
        temp_memory.get_project_context(f"app{i}")

    # Cache should not exceed max size
    assert len(temp_memory._context_cache) <= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
