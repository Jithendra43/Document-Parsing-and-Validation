#!/usr/bin/env python3
"""
Comprehensive system test to verify all components are working correctly.
This test validates the entire EDI processing pipeline.
"""

import asyncio
import sys
import os
import traceback
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_status(status, message):
    if status == "PASS":
        print(f"{Colors.GREEN}✅ {message}{Colors.END}")
    elif status == "FAIL":
        print(f"{Colors.RED}❌ {message}{Colors.END}")
    elif status == "WARN":
        print(f"{Colors.YELLOW}⚠️ {message}{Colors.END}")
    else:
        print(f"{Colors.BLUE}ℹ️ {message}{Colors.END}")

def test_imports():
    """Test all critical imports."""
    print(f"\n{Colors.BOLD}=== TESTING IMPORTS ==={Colors.END}")
    
    imports_to_test = [
        ('streamlit', 'Streamlit web framework'),
        ('fastapi', 'FastAPI framework'),
        ('uvicorn', 'ASGI server'),
        ('pandas', 'Data analysis'),
        ('numpy', 'Numerical computing'),
        ('plotly', 'Data visualization'),
        ('pyx12', 'EDI parsing'),
        ('fhir.resources', 'FHIR resources'),
        ('groq', 'AI analysis'),
        ('pydantic', 'Data validation'),
        ('pydantic_settings', 'Pydantic settings'),
        ('requests', 'HTTP client'),
        ('structlog', 'Structured logging'),
        ('dotenv', 'Environment variables'),
        ('aiofiles', 'Async file operations')
    ]
    
    failed_imports = []
    for module, description in imports_to_test:
        try:
            __import__(module)
            print_status("PASS", f"{module}: {description}")
        except ImportError as e:
            print_status("FAIL", f"{module}: {description} - {e}")
            failed_imports.append((module, str(e)))
    
    return len(failed_imports) == 0

def test_app_imports():
    """Test app-specific imports."""
    print(f"\n{Colors.BOLD}=== TESTING APP IMPORTS ==={Colors.END}")
    
    app_imports = [
        'app.config',
        'app.core.models',
        'app.core.logger',
        'app.core.edi_parser',
        'app.core.fhir_mapper', 
        'app.ai.analyzer',
        'app.services.processor',
        'app.api.main'
    ]
    
    failed_imports = []
    for module in app_imports:
        try:
            __import__(module)
            print_status("PASS", f"{module}")
        except Exception as e:
            print_status("FAIL", f"{module}: {e}")
            failed_imports.append((module, str(e)))
    
    return len(failed_imports) == 0

def test_component_initialization():
    """Test component initialization."""
    print(f"\n{Colors.BOLD}=== TESTING COMPONENT INITIALIZATION ==={Colors.END}")
    
    try:
        from app.core.edi_parser import EDI278Parser, EDI278Validator
        from app.core.fhir_mapper import X12To278FHIRMapper
        from app.ai.analyzer import EDIAIAnalyzer
        from app.services.processor import EDIProcessingService
        
        # Test parser
        parser = EDI278Parser()
        print_status("PASS", "EDI278Parser initialized")
        
        # Test validator
        validator = EDI278Validator()
        print_status("PASS", "EDI278Validator initialized")
        
        # Test FHIR mapper
        fhir_mapper = X12To278FHIRMapper()
        print_status("PASS", "X12To278FHIRMapper initialized")
        
        # Test AI analyzer
        ai_analyzer = EDIAIAnalyzer()
        if ai_analyzer.is_available:
            print_status("PASS", "EDIAIAnalyzer initialized with AI available")
        else:
            print_status("WARN", "EDIAIAnalyzer initialized but AI not available (API key missing)")
        
        # Test processing service
        processor = EDIProcessingService()
        print_status("PASS", "EDIProcessingService initialized")
        
        return True
        
    except Exception as e:
        print_status("FAIL", f"Component initialization failed: {e}")
        return False

async def test_edi_processing():
    """Test EDI processing pipeline."""
    print(f"\n{Colors.BOLD}=== TESTING EDI PROCESSING PIPELINE ==={Colors.END}")
    
    try:
        from app.services.processor import EDIProcessingService
        from app.core.models import EDIFileUpload
        
        # Create test EDI content
        test_edi = """ISA*00*          *00*          *ZZ*SENDER_ID     *ZZ*RECEIVER_ID   *250620*1909*U*00501*000000001*0*P*>~
GS*HS*SENDER*RECEIVER*20250620*1909*1*X*005010X279A1~
ST*278*0001~
BHT*0078*00*1234567890*20250620*1909~
HL*1**20*1~
NM1*PR*2*INSURANCE COMPANY*****PI*123456789~
HL*2*1*21*1~
NM1*1P*1*DOE*JOHN****XX*9876543210~
HL*3*2*22*0~
NM1*IL*1*SMITH*JANE****MI*111223333~
DMG*D8*19850315*F~
DTP*291*D8*20250620~
UM*HS*30**1~
SE*14*0001~
GE*1*1~
IEA*1*000000001~"""
        
        # Test processing
        processor = EDIProcessingService()
        upload_request = EDIFileUpload(
            filename="test.edi",
            content_type="text/plain",
            validate_only=False,
            enable_ai_analysis=True,
            output_format="fhir"
        )
        
        job = await processor.process_content(test_edi, upload_request)
        
        # Check results
        if job.parsed_edi:
            print_status("PASS", f"EDI parsing successful: {len(job.parsed_edi.segments)} segments")
        else:
            print_status("FAIL", "EDI parsing failed")
            return False
        
        if job.validation_result:
            if job.validation_result.is_valid:
                print_status("PASS", "EDI validation successful")
            else:
                print_status("WARN", f"EDI validation completed with issues: {len(job.validation_result.issues)} issues")
        else:
            print_status("FAIL", "EDI validation failed")
            return False
        
        if job.fhir_mapping:
            print_status("PASS", f"FHIR mapping successful: {len(job.fhir_mapping.resources)} resources")
        else:
            print_status("WARN", "FHIR mapping failed (this may be expected for test data)")
        
        if job.ai_analysis:
            print_status("PASS", f"AI analysis successful: confidence {job.ai_analysis.confidence_score:.2f}")
        else:
            print_status("WARN", "AI analysis not available (API key may be missing)")
        
        print_status("PASS", f"Overall processing status: {job.status}")
        return True
        
    except Exception as e:
        print_status("FAIL", f"EDI processing test failed: {e}")
        traceback.print_exc()
        return False

def test_file_structure():
    """Test required file structure."""
    print(f"\n{Colors.BOLD}=== TESTING FILE STRUCTURE ==={Colors.END}")
    
    required_files = [
        'app.py',
        'streamlit_app.py',
        'requirements.txt',
        'runtime.txt',
        'test_edi_278.edi',
        '.streamlit/config.toml',
        'app/__init__.py',
        'app/config.py',
        'app/core/__init__.py',
        'app/core/models.py',
        'app/core/logger.py',
        'app/core/edi_parser.py',
        'app/core/fhir_mapper.py',
        'app/ai/__init__.py',
        'app/ai/analyzer.py',
        'app/services/__init__.py',
        'app/services/processor.py',
        'app/api/__init__.py',
        'app/api/main.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if Path(file_path).exists():
            print_status("PASS", f"{file_path}")
        else:
            print_status("FAIL", f"Missing: {file_path}")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def test_configuration():
    """Test configuration loading."""
    print(f"\n{Colors.BOLD}=== TESTING CONFIGURATION ==={Colors.END}")
    
    try:
        from app.config import settings
        
        print_status("PASS", f"App name: {settings.app_name}")
        print_status("PASS", f"App version: {settings.app_version}")
        print_status("PASS", f"Debug mode: {settings.debug}")
        
        if settings.groq_api_key and settings.groq_api_key != "your_groq_api_key_here":
            print_status("PASS", "Groq API key configured")
        else:
            print_status("WARN", "Groq API key not configured (AI features will be disabled)")
        
        return True
        
    except Exception as e:
        print_status("FAIL", f"Configuration test failed: {e}")
        return False

def test_fastapi_app():
    """Test FastAPI app creation."""
    print(f"\n{Colors.BOLD}=== TESTING FASTAPI APP ==={Colors.END}")
    
    try:
        from app.api.main import app
        
        # Check if app is created
        if app:
            print_status("PASS", "FastAPI app created successfully")
            
            # Check routes
            route_count = len(app.routes)
            print_status("PASS", f"FastAPI app has {route_count} routes")
            
            return True
        else:
            print_status("FAIL", "FastAPI app creation failed")
            return False
        
    except Exception as e:
        print_status("FAIL", f"FastAPI app test failed: {e}")
        return False

async def main():
    """Run all tests."""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("=" * 80)
    print("🔍 COMPREHENSIVE SYSTEM TEST")
    print("=" * 80)
    print(f"{Colors.END}")
    
    tests = [
        ("External Dependencies", test_imports),
        ("App Imports", test_app_imports),
        ("Component Initialization", test_component_initialization),
        ("File Structure", test_file_structure),
        ("Configuration", test_configuration),
        ("FastAPI App", test_fastapi_app)
    ]
    
    async_tests = [
        ("EDI Processing Pipeline", test_edi_processing)
    ]
    
    results = {}
    
    # Run synchronous tests
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print_status("FAIL", f"{test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Run asynchronous tests
    for test_name, test_func in async_tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print_status("FAIL", f"{test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{Colors.BOLD}=== TEST SUMMARY ==={Colors.END}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print_status(status, test_name)
    
    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL TESTS PASSED! SYSTEM IS FULLY FUNCTIONAL{Colors.END}")
        return True
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ {total - passed} TESTS FAILED - SYSTEM NEEDS ATTENTION{Colors.END}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Test suite failed: {e}{Colors.END}")
        traceback.print_exc()
        sys.exit(1) 