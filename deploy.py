#!/usr/bin/env python3
"""
Simple deployment launcher for EDI X12 278 Processor
Streamlit-based application deployment with automated setup.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text.center(60)}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️ {text}{Colors.END}")

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print_success(f"Python {version.major}.{version.minor}.{version.micro} is compatible")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor}.{version.micro} is not compatible")
        print_info("Please upgrade to Python 3.9 or higher")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'streamlit',
        'pyx12',
        'fhir.resources',
        'groq',
        'pandas',
        'plotly'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print_success(f"{package} is installed")
        except ImportError:
            missing_packages.append(package)
            print_warning(f"{package} is missing")
    
    return missing_packages

def install_dependencies():
    """Install missing dependencies."""
    print_info("Installing dependencies from requirements_deploy.txt...")
    
    try:
        if platform.system() == "Windows":
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements_deploy.txt"], 
                         check=True)
        else:
            subprocess.run(["pip", "install", "-r", "requirements_deploy.txt"], check=True)
        
        print_success("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False
    except FileNotFoundError:
        print_error("requirements_deploy.txt not found")
        return False

def check_environment():
    """Check environment variables."""
    groq_key = os.getenv('GROQ_API_KEY')
    
    if groq_key and groq_key != 'your_groq_api_key_here':
        print_success("GROQ_API_KEY is configured")
        return True
    else:
        print_warning("GROQ_API_KEY is not configured")
        print_info("AI features will be limited without a valid API key")
        return False

def create_directories():
    """Create required directories."""
    directories = ['uploads', 'outputs', 'temp', 'logs', '.streamlit']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print_success(f"Directory '{directory}' ready")

def launch_application():
    """Launch the Streamlit application."""
    print_info("Launching EDI X12 278 Processor...")
    
    try:
        # Set environment variables for the session
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path.cwd())
        
        # Launch Streamlit
        if platform.system() == "Windows":
            cmd = [sys.executable, "-m", "streamlit", "run", "streamlit_deploy.py", 
                   "--server.port", "8501", "--server.address", "0.0.0.0"]
        else:
            cmd = ["streamlit", "run", "streamlit_deploy.py", 
                   "--server.port", "8501", "--server.address", "0.0.0.0"]
        
        print_success("Starting Streamlit server...")
        print_info("Access your application at: http://localhost:8501")
        print_info("Press Ctrl+C to stop the server")
        
        subprocess.run(cmd, env=env)
        
    except KeyboardInterrupt:
        print_info("\nApplication stopped by user")
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to start application: {e}")
    except FileNotFoundError:
        print_error("Streamlit not found. Please install it: pip install streamlit")

def show_deployment_options():
    """Show different deployment options."""
    print_header("DEPLOYMENT OPTIONS")
    
    print(f"{Colors.BOLD}1. Local Development (Current){Colors.END}")
    print("   - Runs on localhost:8501")
    print("   - Best for testing and development")
    print("   - Requires Python environment")
    
    print(f"\n{Colors.BOLD}2. Docker Deployment{Colors.END}")
    print("   - Run: docker-compose up --build")
    print("   - Containerized and isolated")
    print("   - Production-ready")
    
    print(f"\n{Colors.BOLD}3. Cloud Deployment{Colors.END}")
    print("   - Streamlit Cloud (easiest)")
    print("   - Heroku, AWS, Azure")
    print("   - Scalable and managed")
    
    print(f"\n{Colors.BOLD}4. Production Server{Colors.END}")
    print("   - Systemd service")
    print("   - Nginx reverse proxy")
    print("   - SSL/HTTPS support")

def main():
    """Main deployment function."""
    print_header("EDI X12 278 PROCESSOR DEPLOYMENT")
    
    # Check system compatibility
    if not check_python_version():
        sys.exit(1)
    
    # Check if we're in the right directory
    if not Path("streamlit_deploy.py").exists():
        print_error("streamlit_deploy.py not found in current directory")
        print_info("Please run this script from the project root directory")
        sys.exit(1)
    
    # Check dependencies
    missing_packages = check_dependencies()
    
    if missing_packages:
        print_warning(f"Missing packages: {', '.join(missing_packages)}")
        response = input("Install missing dependencies? (y/n): ").lower().strip()
        
        if response == 'y':
            if not install_dependencies():
                sys.exit(1)
        else:
            print_error("Cannot proceed without required dependencies")
            sys.exit(1)
    
    # Check environment
    has_groq_key = check_environment()
    
    if not has_groq_key:
        print_info("To enable full AI features, set your GROQ API key:")
        print_info("export GROQ_API_KEY='your_actual_api_key'")
        print_info("Or add it to a .env file")
    
    # Create directories
    create_directories()
    
    # Show deployment options
    show_deployment_options()
    
    # Ask user what they want to do
    print(f"\n{Colors.BOLD}Choose deployment option:{Colors.END}")
    print("1. Launch Local Development Server")
    print("2. Show Docker Commands")
    print("3. Show Cloud Deployment Info")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        launch_application()
    elif choice == "2":
        print_info("Docker deployment commands:")
        print("docker-compose up --build")
        print("Then access: http://localhost:8501")
    elif choice == "3":
        print_info("Cloud deployment:")
        print("1. Push code to GitHub")
        print("2. Connect to share.streamlit.io")
        print("3. Set GROQ_API_KEY in secrets")
        print("4. Deploy!")
    elif choice == "4":
        print_info("Goodbye!")
    else:
        print_error("Invalid choice")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_info("\nDeployment cancelled by user")
    except Exception as e:
        print_error(f"Deployment failed: {e}")
        sys.exit(1) 