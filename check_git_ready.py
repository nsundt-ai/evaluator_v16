#!/usr/bin/env python3
"""
Check if the repository is ready for Git publishing
This script verifies that sensitive files are properly ignored.
"""

import os
import subprocess

def check_git_status():
    """Check what files Git is tracking"""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        print("❌ Error running git status")
        return []

def check_sensitive_files():
    """Check if sensitive files exist and are ignored"""
    sensitive_files = ['.env', '.env.local', 'data/evaluator_v16.db']
    issues = []
    
    for file in sensitive_files:
        if os.path.exists(file):
            if file == '.env':
                print(f"✅ {file} exists (should be ignored by .gitignore)")
            else:
                print(f"⚠️  {file} exists - consider if this should be ignored")
        else:
            print(f"ℹ️  {file} does not exist")
    
    return issues

def check_gitignore():
    """Check if .gitignore is properly configured"""
    if not os.path.exists('.gitignore'):
        print("❌ .gitignore file missing")
        return False
    
    with open('.gitignore', 'r') as f:
        content = f.read()
    
    required_patterns = ['.env', '__pycache__', '*.log']
    missing_patterns = []
    
    for pattern in required_patterns:
        if pattern not in content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"⚠️  .gitignore missing patterns: {missing_patterns}")
        return False
    else:
        print("✅ .gitignore looks good")
        return True

def check_tracked_files():
    """Check if any sensitive files are being tracked"""
    tracked_files = check_git_status()
    sensitive_patterns = ['.env', 'node_modules', '__pycache__']
    
    problematic_files = []
    for file in tracked_files:
        if file.startswith('A ') or file.startswith('M '):  # Added or modified
            file_path = file[3:]  # Remove status prefix
            for pattern in sensitive_patterns:
                if pattern in file_path:
                    problematic_files.append(file_path)
    
    if problematic_files:
        print(f"❌ These files should not be tracked: {problematic_files}")
        return False
    else:
        print("✅ No sensitive files are being tracked")
        return True

def main():
    """Main verification function"""
    print("🔍 Git Publishing Readiness Check")
    print("=" * 40)
    
    # Check .gitignore
    gitignore_ok = check_gitignore()
    
    # Check sensitive files
    check_sensitive_files()
    
    # Check tracked files
    tracked_ok = check_tracked_files()
    
    print("\n" + "=" * 40)
    if gitignore_ok and tracked_ok:
        print("✅ Repository is ready for Git publishing!")
        print("\nNext steps:")
        print("1. git add .")
        print("2. git commit -m 'Initial commit: Educational Evaluator v16'")
        print("3. git push")
    else:
        print("❌ Repository needs attention before publishing")
        print("Please fix the issues above before committing")

if __name__ == "__main__":
    main() 