#!/usr/bin/env python3
"""
Access Verifier - Confirms Claude Code has all necessary development access
"""
import os
import subprocess
import json
import socket
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class AccessVerifier:
    """Verifies access to GitHub, servers, and local system for development work"""

    def __init__(self):
        self.results = {}

    def verify_all(self) -> Dict[str, bool]:
        """Run all verification checks"""
        print("🔍 Verifying development environment access...")

        checks = [
            ("github", self.verify_github_access),
            ("server", self.verify_server_access),
            ("local", self.verify_local_system),
            ("tools", self.verify_development_tools)
        ]

        for check_name, check_func in checks:
            try:
                success, message = check_func()
                self.results[check_name] = {
                    'status': success,
                    'message': message
                }

                if success:
                    print(f"✅ {message}")
                else:
                    print(f"❌ {message}")

            except Exception as e:
                self.results[check_name] = {
                    'status': False,
                    'message': f"Error during check: {e}"
                }
                print(f"❌ {check_name} check failed: {e}")

        return {k: v['status'] for k, v in self.results.items()}

    def verify_github_access(self) -> Tuple[bool, str]:
        """Verify GitHub access via gh CLI or token and git commands"""

        # Check if git is available
        try:
            result = subprocess.run(['git', '--version'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return False, "Git command not available"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "Git command not found or not responding"

        # Check if gh CLI is available and authenticated (preferred method)
        try:
            result = subprocess.run(['gh', 'auth', 'status'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True, "GitHub access confirmed (gh CLI authenticated, git ready)"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # Fall through to token check

        # Fallback: Check for GitHub token environment variable
        github_token = os.getenv('GITHUB_TOKEN')
        if github_token:
            return True, "GitHub access confirmed (GITHUB_TOKEN set, git ready)"

        return False, "GitHub access not configured (no gh auth or GITHUB_TOKEN)"

    def verify_server_access(self) -> Tuple[bool, str]:
        """Verify SSH server access"""

        # Check if SSH is available
        try:
            result = subprocess.run(['ssh', '-V'],
                                  capture_output=True, text=True, timeout=5)
            # SSH outputs version to stderr
            if 'OpenSSH' not in result.stderr and 'OpenSSH' not in result.stdout:
                return False, "SSH client not available"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "SSH client not found"

        # Check for SSH keys
        ssh_dir = Path.home() / '.ssh'
        if not ssh_dir.exists():
            return False, "SSH directory not found (~/.ssh)"

        # Look for common SSH key files
        key_files = ['id_rsa', 'id_ed25519', 'id_ecdsa']
        found_keys = []
        for key_file in key_files:
            if (ssh_dir / key_file).exists():
                found_keys.append(key_file)

        if not found_keys:
            return False, "No SSH private keys found in ~/.ssh"

        # Check SSH agent (optional but helpful)
        ssh_auth_sock = os.getenv('SSH_AUTH_SOCK')
        if ssh_auth_sock:
            try:
                result = subprocess.run(['ssh-add', '-l'],
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return True, f"Server access confirmed (SSH ready, keys loaded: {', '.join(found_keys)})"
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return True, f"Server access available (SSH ready, keys found: {', '.join(found_keys)})"

    def verify_local_system(self) -> Tuple[bool, str]:
        """Verify local system access for development"""

        issues = []

        # Check file system write access
        try:
            test_file = Path('/tmp/recall_test_write')
            test_file.write_text('test')
            test_file.unlink()
        except Exception as e:
            issues.append(f"File write access failed: {e}")

        # Check ability to execute commands
        try:
            result = subprocess.run(['echo', 'test'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0 or result.stdout.strip() != 'test':
                issues.append("Command execution failed")
        except Exception as e:
            issues.append(f"Command execution error: {e}")

        # Check current directory access
        try:
            cwd = os.getcwd()
            os.listdir(cwd)
        except Exception as e:
            issues.append(f"Directory access failed: {e}")

        if issues:
            return False, f"Local system issues: {'; '.join(issues)}"

        return True, "Local system access confirmed (files, commands, directories)"

    def verify_development_tools(self) -> Tuple[bool, str]:
        """Verify common development tools are available"""

        tools = {
            'python3': ['python3', '--version'],
            'node': ['node', '--version'],
            'npm': ['npm', '--version'],
            'curl': ['curl', '--version'],
            'wget': ['wget', '--version']
        }

        available_tools = []
        missing_tools = []

        for tool_name, command in tools.items():
            try:
                result = subprocess.run(command,
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    available_tools.append(tool_name)
                else:
                    missing_tools.append(tool_name)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                missing_tools.append(tool_name)

        if available_tools:
            tools_msg = f"Development tools available: {', '.join(available_tools)}"
            if missing_tools:
                tools_msg += f" (missing: {', '.join(missing_tools)})"
            return True, tools_msg
        else:
            return False, f"No development tools found: {', '.join(missing_tools)}"

    def get_detailed_results(self) -> str:
        """Get formatted results for display"""
        if not self.results:
            return "No verification results available"

        output = []
        output.append("🔍 ACCESS VERIFICATION RESULTS:")
        output.append("=" * 50)

        for category, result in self.results.items():
            status_icon = "✅" if result['status'] else "❌"
            output.append(f"{status_icon} {category.upper()}: {result['message']}")

        # Overall status
        all_passed = all(r['status'] for r in self.results.values())
        output.append("=" * 50)

        if all_passed:
            output.append("🎉 ALL SYSTEMS GO - Claude Code has full development access!")
        else:
            failed_checks = [k for k, v in self.results.items() if not v['status']]
            output.append(f"⚠️ Issues found in: {', '.join(failed_checks)}")
            output.append("💡 Some development capabilities may be limited")

        return "\n".join(output)

    def get_summary_status(self) -> str:
        """Get brief status summary for recall command"""
        if not self.results:
            return "❓ Access verification not run"

        statuses = []
        for category, result in self.results.items():
            icon = "✅" if result['status'] else "❌"
            statuses.append(f"{icon} {category}")

        return " | ".join(statuses)


def quick_verify() -> bool:
    """Quick verification for use in recall command"""
    verifier = AccessVerifier()
    results = verifier.verify_all()
    return all(results.values())


if __name__ == "__main__":
    # Test the verification system
    print("🧪 Testing Access Verification System\n")

    verifier = AccessVerifier()
    results = verifier.verify_all()

    print("\n" + verifier.get_detailed_results())

    print(f"\nQuick status: {verifier.get_summary_status()}")

    overall_success = all(results.values())
    print(f"\n🎯 Overall result: {'SUCCESS' if overall_success else 'ISSUES FOUND'}")