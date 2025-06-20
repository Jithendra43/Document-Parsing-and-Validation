#!/usr/bin/env python3
"""Quick test to verify the EDI system is working properly."""

import json
import sys
from pathlib import Path

def test_parser():
    """Test the EDI parser."""
    try:
        from app.core.edi_parser import EDI278Parser
        parser = EDI278Parser()
        
        # Read sample file
        sample_path = Path("sample_278.edi")
        if sample_path.exists():
            content = sample_path.read_text()
            result = parser.parse_content(content, "sample_278.edi")
            print(f"✅ Parser: {len(result.segments)} segments parsed")
            return True
        else:
            print("❌ Parser: Sample file not found")
            return False
    except Exception as e:
        print(f"❌ Parser failed: {e}")
        return False

def test_validator():
    """Test the EDI validator."""
    try:
        from app.core.edi_parser import EDI278Parser, EDI278Validator
        parser = EDI278Parser()
        validator = EDI278Validator()
        
        # Use minimal test content
        test_content = """ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *230620*1234*^*00501*000000001*0*P*:~
GS*HS*SENDER*RECEIVER*20230620*1234*1*X*005010X279A1~
ST*278*0001*005010X217~
BHT*0078*00*1234567890*20230620*1234~
HL*1**20*1~
NM1*PR*2*INSURANCE COMPANY*****PI*12345~
SE*6*0001~
GE*1*1~
IEA*1*000000001~"""
        
        result = parser.parse_content(test_content, "test.edi")
        validation = validator.validate(result)
        print(f"✅ Validator: {len(validation.issues)} issues found, Valid: {validation.is_valid}")
        return True
    except Exception as e:
        print(f"❌ Validator failed: {e}")
        return False

def test_ai_analyzer():
    """Test AI analyzer initialization."""
    try:
        from app.ai.analyzer import EDIAIAnalyzer
        analyzer = EDIAIAnalyzer()
        print(f"✅ AI Analyzer: Available={analyzer.ai_available}, Provider={analyzer.ai_provider}")
        return True
    except Exception as e:
        print(f"❌ AI Analyzer failed: {e}")
        return False

def test_fhir_mapper():
    """Test FHIR mapper."""
    try:
        from app.core.fhir_mapper import X12To278FHIRMapper
        mapper = X12To278FHIRMapper()
        print("✅ FHIR Mapper: Initialized successfully")
        return True
    except Exception as e:
        print(f"❌ FHIR Mapper failed: {e}")
        return False

def test_processor():
    """Test the processor service."""
    try:
        from app.services.processor import EDIProcessingService
        processor = EDIProcessingService()
        print("✅ Processor Service: Initialized successfully")
        return True
    except Exception as e:
        print(f"❌ Processor Service failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Quick System Test\n")
    
    tests = [
        ("EDI Parser", test_parser),
        ("EDI Validator", test_validator),
        ("AI Analyzer", test_ai_analyzer),
        ("FHIR Mapper", test_fhir_mapper),
        ("Processor Service", test_processor),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test_func in tests:
        print(f"Testing {name}...")
        if test_func():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - System is ready!")
        return 0
    else:
        print("⚠️  Some tests failed - check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 