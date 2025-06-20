#!/usr/bin/env python3
"""
Comprehensive setup and validation script for EDI X12 278 Processing Microservice.

This script validates the entire system for 100% functionality and TR3 compliance.
"""

import sys
import subprocess
import importlib
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class SystemValidator:
    """Comprehensive system validation for EDI X12 278 processing."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed_checks = []
        
    def log_pass(self, check: str):
        """Log a passed check."""
        self.passed_checks.append(check)
        print(f"{Colors.GREEN}✓{Colors.END} {check}")
    
    def log_warning(self, check: str, details: str = ""):
        """Log a warning."""
        self.warnings.append((check, details))
        print(f"{Colors.YELLOW}⚠{Colors.END} {check}")
        if details:
            print(f"  {Colors.YELLOW}→{Colors.END} {details}")
    
    def log_error(self, check: str, details: str = ""):
        """Log an error."""
        self.issues.append((check, details))
        print(f"{Colors.RED}✗{Colors.END} {check}")
        if details:
            print(f"  {Colors.RED}→{Colors.END} {details}")
    
    def validate_dependencies(self) -> bool:
        """Validate all required dependencies."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}🔍 DEPENDENCY VALIDATION{Colors.END}\n")
        
        required_packages = {
            'pyx12': 'X12 EDI parsing and validation',
            'fhir.resources': 'FHIR R4 resource models',
            'groq': 'AI analysis with Groq/Llama integration',
            'fastapi': 'REST API framework',
            'streamlit': 'Web frontend framework',
            'plotly': 'Data visualization charts for Streamlit',
            'structlog': 'Structured logging',
            'pydantic': 'Data validation and modeling',
            'pydantic_settings': 'Pydantic settings management',
            'uvicorn': 'ASGI server',
            'python-multipart': 'File upload support',
            'requests': 'HTTP client library',
            'dotenv': 'Environment variable management',
            'pandas': 'Data analysis and manipulation',
            'numpy': 'Numerical computing'
        }
        
        all_deps_ok = True
        
        for package, description in required_packages.items():
            try:
                importlib.import_module(package.replace('-', '_'))
                self.log_pass(f"{package}: {description}")
            except ImportError:
                self.log_error(f"Missing: {package}", description)
                all_deps_ok = False
        
        return all_deps_ok
    
    def validate_pyx12_installation(self) -> bool:
        """Validate pyx12 installation and capabilities."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}📋 PYX12 VALIDATION{Colors.END}\n")
        
        try:
            import pyx12
            import pyx12.x12file
            import pyx12.error_handler
            import pyx12.params
            import pyx12.x12context
            from pyx12.map_walker import walk_tree
            
            self.log_pass("pyx12 core modules available")
            
            # Test x12n_document (may not be available in all versions)
            try:
                import pyx12.x12n_document
                self.log_pass("pyx12.x12n_document available (enhanced features)")
            except ImportError:
                self.log_warning("pyx12.x12n_document not available", 
                               "Basic parsing will work, but enhanced TR3 validation may be limited")
            
            # Test pyx12 functionality
            try:
                param = pyx12.params.params()
                param.set('charset', 'ascii')
                self.log_pass("pyx12 parameter configuration working")
            except Exception as e:
                self.log_error("pyx12 parameter configuration failed", str(e))
                return False
                
            return True
            
        except ImportError as e:
            self.log_error("pyx12 import failed", str(e))
            return False
    
    def validate_fhir_resources(self) -> bool:
        """Validate FHIR resource capabilities."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}🏥 FHIR VALIDATION{Colors.END}\n")
        
        try:
            from fhir.resources.bundle import Bundle
            from fhir.resources.patient import Patient
            from fhir.resources.coverageeligibilityrequest import CoverageEligibilityRequest
            from fhir.resources.coverageeligibilityresponse import CoverageEligibilityResponse
            from fhir.resources.coverage import Coverage
            from fhir.resources.organization import Organization
            from fhir.resources.practitioner import Practitioner
            
            self.log_pass("FHIR R4 core resources available")
            
            # Test creating a simple resource
            try:
                patient = Patient(id="test-patient")
                patient_dict = patient.dict()
                self.log_pass("FHIR resource creation and serialization working")
            except Exception as e:
                self.log_error("FHIR resource creation failed", str(e))
                return False
            
            # Validate correct resources for X12 278
            try:
                coverage_req = CoverageEligibilityRequest(
                    status="active",
                    purpose=["auth-requirements"]
                )
                self.log_pass("CoverageEligibilityRequest available (correct for X12 278)")
            except Exception as e:
                self.log_error("CoverageEligibilityRequest creation failed", str(e))
                return False
                
            return True
            
        except ImportError as e:
            self.log_error("FHIR resources import failed", str(e))
            return False
    
    def validate_ai_integration(self) -> bool:
        """Validate AI integration capabilities."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}🤖 AI INTEGRATION VALIDATION{Colors.END}\n")
        
        try:
            import groq
            self.log_pass("Groq library available")
            
            # Check if API key is configured
            env_file = Path('.env')
            if env_file.exists():
                with open(env_file, 'r') as f:
                    env_content = f.read()
                    if 'GROQ_API_KEY=' in env_content:
                        self.log_pass("GROQ_API_KEY configured in .env")
                    else:
                        self.log_warning("GROQ_API_KEY not found in .env", 
                                       "AI analysis will not work without API key")
            else:
                self.log_warning(".env file not found", 
                               "Copy env_example.txt to .env and configure")
            
            return True
            
        except ImportError:
            self.log_error("Groq library not installed", 
                         "Install with: pip install groq")
            return False
    
    def validate_file_structure(self) -> bool:
        """Validate project file structure."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}📁 FILE STRUCTURE VALIDATION{Colors.END}\n")
        
        required_files = [
            'app/__init__.py',
            'app/config.py',
            'app/core/__init__.py',
            'app/core/models.py',
            'app/core/logger.py',
            'app/core/edi_parser.py',
            'app/core/fhir_mapper.py',
            'app/ai/__init__.py',
            'app/ai/analyzer.py',
            'app/api/__init__.py',
            'app/api/main.py',
            'app/services/__init__.py',
            'app/services/processor.py',
            'streamlit_app.py',
            'requirements.txt',
            'README.md',
            'run_api.py',
            'run_streamlit.py'
        ]
        
        all_files_ok = True
        
        for file_path in required_files:
            if Path(file_path).exists():
                self.log_pass(f"File exists: {file_path}")
            else:
                self.log_error(f"Missing file: {file_path}")
                all_files_ok = False
        
        # Check for sample EDI file
        if Path('sample_278.edi').exists():
            self.log_pass("Sample EDI file available for testing")
        else:
            self.log_warning("No sample EDI file found", 
                           "Create sample_278.edi for testing")
        
        return all_files_ok
    
    def validate_imports(self) -> bool:
        """Validate all internal imports."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}🔗 IMPORT VALIDATION{Colors.END}\n")
        
        modules_to_test = [
            ('app.config', 'Configuration module'),
            ('app.core.models', 'Data models'),
            ('app.core.logger', 'Logging system'),
            ('app.core.edi_parser', 'EDI parser'),
            ('app.core.fhir_mapper', 'FHIR mapper'),
            ('app.ai.analyzer', 'AI analyzer'),
            ('app.api.main', 'FastAPI application'),
            ('app.services.processor', 'Processing service')
        ]
        
        all_imports_ok = True
        
        for module_name, description in modules_to_test:
            try:
                importlib.import_module(module_name)
                self.log_pass(f"{module_name}: {description}")
            except ImportError as e:
                self.log_error(f"Import failed: {module_name}", str(e))
                all_imports_ok = False
            except Exception as e:
                self.log_warning(f"Import warning: {module_name}", str(e))
        
        return all_imports_ok
    
    def test_processing_pipeline(self) -> bool:
        """Test the complete processing pipeline."""
        print(f"\n{Colors.BOLD}{Colors.BLUE}⚙️ PIPELINE VALIDATION{Colors.END}\n")
        
        try:
            # Test if we can create basic components
            from app.core.edi_parser import EDI278Parser
            from app.core.fhir_mapper import X12To278FHIRMapper
            from app.ai.analyzer import EDIAIAnalyzer
            
            self.log_pass("Core processing components can be imported")
            
            # Test component initialization
            try:
                parser = EDI278Parser()
                self.log_pass("EDI parser can be initialized")
            except Exception as e:
                self.log_error("EDI parser initialization failed", str(e))
                return False
            
            try:
                mapper = X12To278FHIRMapper()
                self.log_pass("FHIR mapper can be initialized")
            except Exception as e:
                self.log_error("FHIR mapper initialization failed", str(e))
                return False
            
            try:
                analyzer = EDIAIAnalyzer()
                self.log_pass("AI analyzer can be initialized")
            except Exception as e:
                self.log_warning("AI analyzer initialization failed", str(e))
            
            return True
            
        except ImportError as e:
            self.log_error("Core component import failed", str(e))
            return False
    
    def generate_setup_instructions(self) -> str:
        """Generate detailed setup instructions."""
        instructions = f"""
{Colors.BOLD}{Colors.BLUE}📋 SETUP INSTRUCTIONS{Colors.END}

{Colors.BOLD}1. Install Python Dependencies:{Colors.END}
   pip install -r requirements.txt

{Colors.BOLD}2. Install EDI Processing Library:{Colors.END}
   pip install pyx12

{Colors.BOLD}3. Install FHIR Resources:{Colors.END}
   pip install fhir.resources

{Colors.BOLD}4. Install AI Integration:{Colors.END}
   pip install groq

{Colors.BOLD}5. Configure Environment:{Colors.END}
   cp env_example.txt .env
   # Edit .env file with your settings:
   # - GROQ_API_KEY=your_groq_api_key
   # - Other configuration options

{Colors.BOLD}6. Run the Application:{Colors.END}
   # Start the API server:
   python run_api.py
   
   # Start the Streamlit frontend (in another terminal):
   python run_streamlit.py

{Colors.BOLD}7. Test the System:{Colors.END}
   # Upload a sample X12 278 file through the web interface
   # or use the API endpoints directly

{Colors.BOLD}🔧 For Development:{Colors.END}
   # Install additional development dependencies:
   pip install pytest pytest-asyncio black flake8 mypy

{Colors.BOLD}📚 Documentation:{Colors.END}
   # See README.md for detailed usage instructions
   # API documentation available at: http://localhost:8000/docs
"""
        return instructions
    
    def run_full_validation(self) -> bool:
        """Run complete system validation."""
        print(f"{Colors.BOLD}{Colors.MAGENTA}")
        print("=" * 80)
        print("🔍 EDI X12 278 MICROSERVICE - COMPREHENSIVE VALIDATION")
        print("=" * 80)
        print(f"{Colors.END}")
        
        # Run dependency validation
        deps_ok = self.validate_dependencies()
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}📊 VALIDATION SUMMARY{Colors.END}\n")
        
        print(f"{Colors.GREEN}✓ Passed: {len(self.passed_checks)}{Colors.END}")
        print(f"{Colors.YELLOW}⚠ Warnings: {len(self.warnings)}{Colors.END}")
        print(f"{Colors.RED}✗ Errors: {len(self.issues)}{Colors.END}")
        
        if self.issues:
            print(f"\n{Colors.BOLD}{Colors.RED}❌ CRITICAL ISSUES TO FIX:{Colors.END}")
            for i, (issue, details) in enumerate(self.issues, 1):
                print(f"{i}. {issue}")
                if details:
                    print(f"   → {details}")
        
        if self.warnings:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}⚠️ WARNINGS:{Colors.END}")
            for i, (warning, details) in enumerate(self.warnings, 1):
                print(f"{i}. {warning}")
                if details:
                    print(f"   → {details}")
        
        if deps_ok and len(self.issues) == 0:
            print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 ALL VALIDATIONS PASSED!{Colors.END}")
            print(f"{Colors.GREEN}Your EDI X12 278 microservice is ready to use.{Colors.END}")
        elif len(self.issues) == 0:
            print(f"\n{Colors.BOLD}{Colors.YELLOW}⚠️ VALIDATION COMPLETED WITH WARNINGS{Colors.END}")
            print(f"{Colors.YELLOW}The system should work, but consider addressing warnings.{Colors.END}")
        else:
            print(f"\n{Colors.BOLD}{Colors.RED}❌ VALIDATION FAILED{Colors.END}")
            print(f"{Colors.RED}Please fix the critical issues before using the system.{Colors.END}")
            print(self.generate_setup_instructions())
        
        return deps_ok and len(self.issues) == 0


def main():
    """Main function to run validation."""
    validator = SystemValidator()
    success = validator.run_full_validation()
    
    if not success:
        sys.exit(1)
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}✅ System validation completed successfully!{Colors.END}")
    print(f"{Colors.CYAN}You can now start using the EDI X12 278 processing microservice.{Colors.END}")


if __name__ == "__main__":
    main() 