#!/usr/bin/env python3
"""
Setup script for Recall - Project Memory System
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def setup_recall():
    """Set up recall for global usage"""
    print("🔧 Setting up Recall - Project Memory System")

    # Get current directory (should be the recall directory)
    recall_dir = Path(__file__).parent.absolute()
    print(f"📁 Recall directory: {recall_dir}")

    # Test database creation
    print("\n🗄️ Testing database system...")
    try:
        from database import RecallDatabase
        db = RecallDatabase()
        print("✅ Database system working")
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

    # Test project memory
    print("\n🧠 Testing project memory system...")
    try:
        from project_memory import ProjectMemory
        memory = ProjectMemory()
        print("✅ Project memory system working")
    except Exception as e:
        print(f"❌ Project memory test failed: {e}")
        return False

    # Make recall.py executable
    recall_script = recall_dir / "recall.py"
    if recall_script.exists():
        os.chmod(recall_script, 0o755)
        print("✅ Made recall.py executable")

    # Create symlink in ~/bin if it exists
    bin_dir = Path.home() / "bin"
    if bin_dir.exists():
        symlink_path = bin_dir / "recall"
        if symlink_path.exists():
            symlink_path.unlink()  # Remove existing symlink

        try:
            symlink_path.symlink_to(recall_script)
            print(f"✅ Created symlink: {symlink_path} -> {recall_script}")
            print("💡 You can now use 'recall' from anywhere!")
        except Exception as e:
            print(f"⚠️ Could not create symlink: {e}")
            print(f"💡 You can manually add this to PATH: {recall_script}")
    else:
        print("⚠️ ~/bin directory not found")
        print(f"💡 You can run recall directly: {recall_script}")

    print("\n🎉 Recall setup complete!")
    print("\n🚀 Try these commands:")
    print("  recall --list                    # List projects")
    print("  recall test-project --create     # Create test project")
    print("  recall test-project              # Load project context")

    return True

if __name__ == "__main__":
    success = setup_recall()
    sys.exit(0 if success else 1)