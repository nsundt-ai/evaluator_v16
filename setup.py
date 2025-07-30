#!/usr/bin/env python3
"""
Setup script for Educational Evaluator v16
This script helps users set up the environment and dependencies.
"""

import os
import sys
import subprocess
import shutil

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version}")
    return True

def install_requirements():
    """Install required packages"""
    print("\n📦 Installing requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing requirements: {e}")
        return False

def create_env_file():
    """Create .env file from template"""
    env_file = ".env"
    env_example = "env.example"
    
    if os.path.exists(env_file):
        print(f"✅ {env_file} already exists")
        return True
    
    if os.path.exists(env_example):
        shutil.copy(env_example, env_file)
        print(f"✅ Created {env_file} from template")
        print("⚠️  Please edit .env and add your API keys")
        return True
    else:
        print(f"❌ {env_example} not found")
        return False

def check_env_keys():
    """Check if API keys are set"""
    required_keys = ['ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'GEMINI_API_KEY']
    missing_keys = []
    
    for key in required_keys:
        if not os.getenv(key):
            missing_keys.append(key)
    
    if missing_keys:
        print(f"⚠️  Missing API keys: {', '.join(missing_keys)}")
        print("Please add them to your .env file")
        return False
    else:
        print("✅ All API keys are set")
        return True

def main():
    """Main setup function"""
    print("🚀 Educational Evaluator v16 Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install requirements
    if not install_requirements():
        sys.exit(1)
    
    # Create .env file
    if not create_env_file():
        sys.exit(1)
    
    # Check API keys
    check_env_keys()
    
    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env file and add your API keys")
    print("2. Run: streamlit run app.py")
    print("3. Open http://localhost:8501 in your browser")

if __name__ == "__main__":
    main() 