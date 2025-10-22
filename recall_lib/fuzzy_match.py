#!/usr/bin/env python3
"""
Fuzzy matching utilities for better error messages and suggestions
"""
from difflib import SequenceMatcher
from typing import List, Tuple


def similarity_ratio(str1: str, str2: str) -> float:
    """
    Calculate similarity ratio between two strings (0.0 to 1.0)

    Args:
        str1: First string
        str2: Second string

    Returns:
        Similarity ratio (1.0 = identical, 0.0 = completely different)
    """
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def find_similar_strings(
    target: str,
    candidates: List[str],
    threshold: float = 0.6,
    max_results: int = 3
) -> List[Tuple[str, float]]:
    """
    Find similar strings from a list of candidates

    Args:
        target: Target string to match against
        candidates: List of candidate strings
        threshold: Minimum similarity ratio (0.0 to 1.0)
        max_results: Maximum number of results to return

    Returns:
        List of (candidate, similarity) tuples, sorted by similarity
    """
    matches = []

    for candidate in candidates:
        ratio = similarity_ratio(target, candidate)
        if ratio >= threshold:
            matches.append((candidate, ratio))

    # Sort by similarity (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)

    return matches[:max_results]


def get_suggestion_message(
    target: str,
    candidates: List[str],
    threshold: float = 0.6
) -> str:
    """
    Get a formatted suggestion message for similar strings

    Args:
        target: Target string that wasn't found
        candidates: List of valid candidates
        threshold: Minimum similarity ratio

    Returns:
        Formatted suggestion message or empty string if no matches
    """
    similar = find_similar_strings(target, candidates, threshold, max_results=3)

    if not similar:
        return ""

    if len(similar) == 1:
        return f"💡 Did you mean '{similar[0][0]}'?"
    else:
        suggestions = ", ".join([f"'{match[0]}'" for match in similar])
        return f"💡 Did you mean one of: {suggestions}?"


def suggest_project(project_name: str, memory) -> str:
    """
    Get project suggestions when a project is not found

    Args:
        project_name: Project name that wasn't found
        memory: ProjectMemory instance

    Returns:
        Formatted suggestion message
    """
    from .logger import get_logger
    logger = get_logger(__name__)

    # Get all project names
    all_projects = memory.list_all_projects()
    project_names = [p['name'] for p in all_projects]

    # First try fuzzy matching
    suggestion = get_suggestion_message(project_name, project_names, threshold=0.6)

    if suggestion:
        return suggestion

    # No close matches - provide helpful alternatives
    if not all_projects:
        return f"💡 No projects yet! Create one with: recall {project_name} --create"
    elif len(all_projects) <= 5:
        # Show all projects if there are only a few
        project_list = ", ".join([f"'{p}'" for p in project_names[:5]])
        return f"💡 Available projects: {project_list}\n💡 Or create new: recall {project_name} --create"
    else:
        # Show count and suggest listing
        return f"💡 You have {len(all_projects)} projects. List them with: recall --list\n💡 Or create new: recall {project_name} --create"
