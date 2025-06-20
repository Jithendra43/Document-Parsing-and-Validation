#!/usr/bin/env python3
"""
Quick Setup Script for EDI X12 278 Processing Microservice
Guides you through the complete setup process step by step.
"""

import os
import sys
import subprocess
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Print a colored header."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}")
    print(f"🏥 {text}")
    print(f"{'='*60}{Colors.END}")

def print_step(step_num, text):
    """Print a step with number."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}Step {step_num}: {text}{Colors.END}")

def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️ {text}{Colors.END}")

def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 3.8+ required. You have Python {version.major}.{version.minor}")
        return False
    print_success(f"Python {version.major}.{version.minor}.{version.micro} ✓")
    return True

def create_env_file():
    """Create .env file from template."""
    env_template = """# EDI X12 278 Processing Microservice Configuration

# Application Settings
DEBUG=false
APP_NAME="EDI X12 278 Processor"
APP_VERSION="0.1.0"

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_PREFIX="/api/v1"

# Streamlit Configuration
STREAMLIT_HOST=0.0.0.0
STREAMLIT_PORT=8501

# File Processing
MAX_FILE_SIZE=52428800
UPLOAD_DIR=./uploads
OUTPUT_DIR=./outputs
TEMP_DIR=./temp

# Database
DATABASE_URL=sqlite:///./edi_processor.db

# Redis (optional - can leave as default)
REDIS_URL=redis://localhost:6379/0

# AI/ML Configuration (Groq API) - ADD YOUR KEY HERE
GROQ_API_KEY=your_groq_api_key_here

# Alternative AI Configuration (OpenAI) - Optional
# OPENAI_API_KEY=your_openai_api_key_here

# AI Model Selection
AI_MODEL=llama3-70b-8192

# FHIR Configuration
FHIR_BASE_URL=http://localhost:8080/fhir
FHIR_VERSION=R4

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security
SECRET_KEY=your-secret-key-change-in-production-please-use-random-string
ALLOWED_ORIGINS=["*"]

# EDI Processing
VALIDATE_SEGMENTS=true
STRICT_VALIDATION=false
"""
    
    env_path = Path(".env")
    if env_path.exists():
        response = input(f"{Colors.YELLOW}⚠️ .env file already exists. Overwrite? (y/N): {Colors.END}")
        if response.lower() != 'y':
            print("Keeping existing .env file")
            return True
    
    try:
        env_path.write_text(env_template)
        print_success(".env file created successfully!")
        return True
    except Exception as e:
        print_error(f"Failed to create .env file: {e}")
        return False

def get_groq_api_key():
    """Guide user to get Groq API key."""
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}🤖 AI Configuration (Groq API){Colors.END}")
    print("The AI features require a Groq API key for intelligent analysis.")
    print(f"\n{Colors.CYAN}To get your FREE Groq API key:{Colors.END}")
    print("1. Go to: https://console.groq.com/")
    print("2. Sign up for a free account")
    print("3. Navigate to 'API Keys' section")
    print("4. Create a new API key")
    print("5. Copy the key (starts with 'gsk_...')")
    
    print(f"\n{Colors.YELLOW}💡 Note: Groq offers FREE tier with generous limits for testing!{Colors.END}")
    
    api_key = input(f"\n{Colors.BOLD}Enter your Groq API key (or press Enter to skip): {Colors.END}").strip()
    
    if api_key and api_key != "your_groq_api_key_here":
        # Update .env file with the API key
        env_path = Path(".env")
        if env_path.exists():
            content = env_path.read_text()
            content = content.replace("GROQ_API_KEY=your_groq_api_key_here", f"GROQ_API_KEY={api_key}")
            env_path.write_text(content)
            print_success("API key updated in .env file!")
        return True
    else:
        print_warning("Skipping AI features (you can add the key later in .env file)")
        return False

def install_dependencies():
    """Install Python dependencies."""
    print("Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print_success("Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        print("Try running manually: pip install -r requirements.txt")
        return False

def create_directories():
    """Create required directories."""
    directories = ["uploads", "outputs", "temp"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    print_success(f"Created directories: {', '.join(directories)}")

def run_validation():
    """Run the validation script."""
    print("Running system validation...")
    try:
        result = subprocess.run([sys.executable, "setup_and_validate.py"], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print_success("System validation passed!")
            return True
        else:
            print_warning("Validation completed with warnings")
            print(result.stdout)
            return True
    except Exception as e:
        print_error(f"Validation failed: {e}")
        return False

def show_run_instructions():
    """Show how to run the application."""
    print(f"\n{Colors.GREEN}{Colors.BOLD}🚀 Ready to Launch!{Colors.END}")
    print(f"\n{Colors.CYAN}{Colors.BOLD}Option 1: Run Both Services (Recommended){Colors.END}")
    print("Terminal 1 (API Backend):")
    print(f"  {Colors.YELLOW}python run_api.py{Colors.END}")
    print("\nTerminal 2 (Streamlit Frontend):")
    print(f"  {Colors.YELLOW}python run_streamlit.py{Colors.END}")
    
    print(f"\n{Colors.CYAN}{Colors.BOLD}Option 2: API Only{Colors.END}")
    print(f"  {Colors.YELLOW}python run_api.py{Colors.END}")
    print("  Then visit: http://localhost:8000/docs")
    
    print(f"\n{Colors.CYAN}{Colors.BOLD}Option 3: Development Mode{Colors.END}")
    print("API with auto-reload:")
    print(f"  {Colors.YELLOW}uvicorn app.api.main:app --reload --port 8000{Colors.END}")
    print("Streamlit with auto-reload:")
    print(f"  {Colors.YELLOW}streamlit run streamlit_app.py --server.port 8501{Colors.END}")
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}Access Points:{Colors.END}")
    print("• Streamlit UI: http://localhost:8501")
    print("• API Documentation: http://localhost:8000/docs")
    print("• Health Check: http://localhost:8000/health")
    print("• Statistics: http://localhost:8000/stats")

def show_sample_usage():
    """Show sample usage examples."""
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}📋 Sample Usage{Colors.END}")
    print(f"\n{Colors.CYAN}1. Using Streamlit UI:{Colors.END}")
    print("   • Upload sample_278.edi file")
    print("   • Enable AI Analysis")
    print("   • Choose FHIR output format")
    print("   • View validation results and FHIR resources")
    
    print(f"\n{Colors.CYAN}2. Using REST API:{Colors.END}")
    print("   # Upload file")
    print('   curl -X POST "http://localhost:8000/upload" \\')
    print('     -F "file=@sample_278.edi" \\')
    print('     -F "enable_ai_analysis=true"')
    
    print("\n   # Validate content")
    print('   curl -X POST "http://localhost:8000/validate" \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"content": "ISA*00*...", "enable_ai_analysis": true}\'')

def main():
    """Main setup function."""
    print_header("EDI X12 278 Processing Microservice Setup")
    print("Welcome! This script will guide you through the complete setup process.")
    
    # Step 1: Check Python version
    print_step(1, "Checking Python Version")
    if not check_python_version():
        return False
    
    # Step 2: Create .env file
    print_step(2, "Creating Configuration File (.env)")
    if not create_env_file():
        return False
    
    # Step 3: Get API key
    print_step(3, "AI Configuration (Optional but Recommended)")
    get_groq_api_key()
    
    # Step 4: Install dependencies
    print_step(4, "Installing Dependencies")
    if not install_dependencies():
        print_warning("You may need to install dependencies manually:")
        print("pip install -r requirements.txt")
        input("Press Enter after installing dependencies...")
    
    # Step 5: Create directories
    print_step(5, "Creating Required Directories")
    create_directories()
    
    # Step 6: Run validation
    print_step(6, "Running System Validation")
    run_validation()
    
    # Step 7: Show run instructions
    print_step(7, "Launch Instructions")
    show_run_instructions()
    
    # Step 8: Show sample usage
    show_sample_usage()
    
    print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 Setup Complete!{Colors.END}")
    print(f"{Colors.CYAN}Your EDI X12 278 Processing Microservice is ready to use!{Colors.END}")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Setup interrupted by user.{Colors.END}")
    except Exception as e:
        print_error(f"Setup failed: {e}")
        sys.exit(1) 