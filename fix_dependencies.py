#!/usr/bin/env python3
"""Fix dependencies and setup issues for the EDI processor."""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and show the result."""
    print(f"\n🔧 {description}")
    print(f"Running: {cmd}")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ SUCCESS: {description}")
            if result.stdout:
                print(result.stdout.strip())
        else:
            print(f"❌ FAILED: {description}")
            if result.stderr:
                print(f"Error: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False

def main():
    """Fix common dependency issues."""
    
    print("🔍 EDI X12 278 Processor - Dependency Fixer")
    print("=" * 50)
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Install/upgrade core dependencies
    dependencies = [
        ("pip", "Upgrading pip"),
        ("pydantic", "Installing Pydantic"),
        ("pydantic-settings", "Installing Pydantic Settings"),
        ("structlog", "Installing Structured Logging"),
        ("streamlit", "Installing/Upgrading Streamlit"),
        ("fastapi", "Installing FastAPI"),
        ("uvicorn", "Installing Uvicorn"),
        ("requests", "Installing Requests"),
        ("pandas", "Installing Pandas"),
        ("plotly", "Installing Plotly"),
        ("python-multipart", "Installing Multipart"),
    ]
    
    # Optional AI dependencies
    optional_deps = [
        ("groq", "Installing Groq AI (optional)"),
        ("fhir.resources", "Installing FHIR Resources (optional)"),
        ("pyx12", "Installing pyx12 EDI Parser (optional)"),
    ]
    
    print("\n📦 Installing Core Dependencies...")
    
    for dep, desc in dependencies:
        success = run_command(f"pip install --upgrade {dep}", desc)
        if not success:
            print(f"⚠️ Warning: {dep} installation failed")
    
    print("\n📦 Installing Optional Dependencies...")
    
    for dep, desc in optional_deps:
        success = run_command(f"pip install {dep}", desc)
        if not success:
            print(f"⚠️ Note: {dep} is optional and can be skipped")
    
    # Create required directories
    print("\n📁 Creating Required Directories...")
    
    directories = ["uploads", "outputs", "temp", "logs"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    # Test imports
    print("\n🧪 Testing Critical Imports...")
    
    critical_imports = [
        ("streamlit", "import streamlit"),
        ("pydantic", "from pydantic import BaseModel"),
        ("requests", "import requests"),
        ("pandas", "import pandas"),
    ]
    
    all_good = True
    for name, import_stmt in critical_imports:
        try:
            exec(import_stmt)
            print(f"✅ {name}: OK")
        except ImportError as e:
            print(f"❌ {name}: FAILED - {e}")
            all_good = False
    
    # Final recommendations
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 SETUP COMPLETE!")
        print("\nNext steps:")
        print("1. Test with: streamlit run simple_streamlit.py")
        print("2. If that works: streamlit run app.py")
        print("3. For API: python -m uvicorn app.api.main:app --reload")
    else:
        print("⚠️ SOME ISSUES FOUND")
        print("\nTroubleshooting:")
        print("1. Try installing in a virtual environment")
        print("2. Use Python 3.9-3.11 instead of 3.13 if possible")
        print("3. Check for package conflicts")
    
    print(f"\nCurrent directory: {os.getcwd()}")
    print("Files created: simple_streamlit.py, fix_dependencies.py")

if __name__ == "__main__":
    main() 