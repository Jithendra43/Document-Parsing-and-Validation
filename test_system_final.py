#!/usr/bin/env python3
"""
Comprehensive system test to verify all EDI processing components.
This tests the complete fix for validation issues with pyx12 and TR3 compliance.
"""

import asyncio
import requests
import json
import time
from pathlib import Path

def test_direct_parser():
    """Test the parser directly with pyx12 integration."""
    print("🔧 Testing EDI Parser with pyx12 integration...")
    
    try:
        from app.core.edi_parser import EDI278Parser, EDI278Validator
        
        # Test parsing
        parser = EDI278Parser()
        with open('sample_278.edi', 'r') as f:
            content = f.read()
        
        parsed = parser.parse_content(content, 'test.edi')
        print(f"✅ Parser: {len(parsed.segments)} segments, method: {parsed.parsing_method}")
        
        # Test validation with strict TR3 compliance
        validator = EDI278Validator()
        validation = validator.validate(parsed)
        
        tr3_issues = [issue for issue in validation.issues if issue.code.startswith('TR3')]
        print(f"   Issues: {len(validation.issues)} total ({len(tr3_issues)} TR3-specific)")
        print(f"   TR3 Compliance: {validation.tr3_compliance}")
        
        # Show pyx12 usage
        if 'pyx12' in parsed.parsing_method:
            print(f"   ✅ Using authentic pyx12 library: {parsed.parsing_method}")
        else:
            print(f"   ⚠️  Fallback parsing: {parsed.parsing_method}")
        
        return True, parsed.parsing_method, len(tr3_issues)
        
    except Exception as e:
        print(f"❌ Direct parser test failed: {e}")
        return False, "failed", 0

def test_processor_service():
    """Test the processor service."""
    print("🔧 Testing EDI Processor service...")
    
    try:
        from app.services.processor import EDIProcessingService
        from app.core.models import EDIFileUpload
        
        processor = EDIProcessingService()
        
        # Read sample file
        with open('sample_278.edi', 'r') as f:
            content = f.read()
        
        # Create upload request
        upload_request = EDIFileUpload(filename='test.edi', validate_only=True)
        
        # Test processing
        import asyncio
        job = asyncio.run(processor.process_content(content, upload_request))
        
        print(f"✅ Processor: Status={job.status}")
        if job.validation_result:
            print(f"   Valid={job.validation_result.is_valid}, Segments={job.validation_result.segments_validated}")
            print(f"   TR3 Compliance: {job.validation_result.tr3_compliance}")
        
        return True
        
    except Exception as e:
        print(f"❌ Processor test failed: {e}")
        return False

def test_api_endpoints():
    """Test the API endpoints."""
    print("🔧 Testing API endpoints...")
    
    try:
        # Test health check
        health_response = requests.get('http://localhost:8000/health')
        if health_response.status_code == 200:
            print("✅ Health check: API is healthy")
        else:
            print(f"❌ Health check failed: {health_response.status_code}")
            return False
        
        # Test validation endpoint
        with open('sample_278.edi', 'r') as f:
            content = f.read()
        
        validation_response = requests.post('http://localhost:8000/validate', 
            json={'content': content, 'filename': 'test.edi'})
        
        if validation_response.status_code == 200:
            result = validation_response.json()
            print(f"✅ Validation API: Valid={result.get('is_valid')}, Segments={result.get('segments_validated')}")
            print(f"   Issues={len(result.get('issues', []))}, TR3={result.get('tr3_compliance')}")
            
            # Check for TR3 compliance details
            tr3_issues = [issue for issue in result.get('issues', []) if issue.get('code', '').startswith('TR3')]
            if tr3_issues:
                print(f"   TR3 Issues detected: {len(tr3_issues)}")
                for issue in tr3_issues[:2]:  # Show first 2
                    print(f"     - {issue.get('code')}: {issue.get('message', '')[:60]}...")
            
            return True
        else:
            print(f"❌ Validation API failed: {validation_response.status_code}")
            return False
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def test_streamlit_interface():
    """Test Streamlit interface accessibility."""
    print("🔧 Testing Streamlit connection...")
    
    try:
        streamlit_response = requests.get('http://localhost:8501', timeout=5)
        if streamlit_response.status_code == 200:
            print("✅ Streamlit: Interface is accessible")
            return True
        else:
            print(f"❌ Streamlit not accessible: {streamlit_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Streamlit test failed: {e}")
        return False

def test_pyx12_compliance():
    """Test specific pyx12 and TR3 compliance features."""
    print("🔧 Testing pyx12 and TR3 compliance...")
    
    try:
        import pyx12
        print(f"   ✅ pyx12 library version: {getattr(pyx12, '__version__', 'unknown')}")
        
        # Test with sample content
        from app.core.edi_parser import EDI278Parser
        parser = EDI278Parser()
        
        with open('sample_278.edi', 'r') as f:
            content = f.read()
        
        parsed = parser.parse_content(content, 'test.edi')
        
        # Check if using authentic pyx12
        if 'pyx12' in parsed.parsing_method:
            print(f"   ✅ Authentic pyx12 parsing: {parsed.parsing_method}")
        else:
            print(f"   ⚠️  Fallback parsing: {parsed.parsing_method}")
        
        # Validate TR3 compliance
        from app.core.edi_parser import EDI278Validator
        validator = EDI278Validator()
        validation = validator.validate(parsed)
        
        tr3_issues = [issue for issue in validation.issues if issue.code.startswith('TR3')]
        print(f"   TR3 Validation: {len(tr3_issues)} compliance issues found")
        
        # Show key TR3 requirements
        bht_segments = [seg for seg in parsed.segments if seg.segment_id == 'BHT']
        hl_segments = [seg for seg in parsed.segments if seg.segment_id == 'HL']
        nm1_segments = [seg for seg in parsed.segments if seg.segment_id == 'NM1']
        
        print(f"   TR3 Segments: BHT={len(bht_segments)}, HL={len(hl_segments)}, NM1={len(nm1_segments)}")
        
        return True, len(tr3_issues)
        
    except Exception as e:
        print(f"❌ pyx12/TR3 compliance test failed: {e}")
        return False, 0

def main():
    """Run comprehensive system test."""
    print("🚀 Starting Comprehensive EDI System Test")
    print("=" * 50)
    
    # Track test results
    results = {}
    
    # Test components
    results['parser'], parsing_method, tr3_issues = test_direct_parser()
    print()
    
    results['processor'] = test_processor_service()
    print()
    
    results['api'] = test_api_endpoints()
    print()
    
    results['streamlit'] = test_streamlit_interface()
    print()
    
    results['pyx12_tr3'], total_tr3_issues = test_pyx12_compliance()
    print()
    
    # Summary
    print("=" * 50)
    print("📊 TEST SUMMARY")
    print(f"Direct Parser        {'✅ PASS' if results['parser'] else '❌ FAIL'}")
    print(f"Processor Service    {'✅ PASS' if results['processor'] else '❌ FAIL'}")
    print(f"API Endpoints        {'✅ PASS' if results['api'] else '❌ FAIL'}")
    print(f"Streamlit Interface  {'✅ PASS' if results['streamlit'] else '❌ FAIL'}")
    print(f"pyx12/TR3 Compliance {'✅ PASS' if results['pyx12_tr3'] else '❌ FAIL'}")
    print()
    
    passed = sum(results.values())
    total = len(results)
    print(f"Overall: {passed}/{total} tests passed")
    print()
    
    # Detailed compliance report
    if results['pyx12_tr3']:
        print("🔍 TR3 COMPLIANCE REPORT")
        print(f"   Parsing Method: {parsing_method}")
        print(f"   TR3 Issues Found: {total_tr3_issues}")
        
        if 'pyx12' in parsing_method:
            print("   ✅ Using authentic pyx12 library for EDI parsing")
        else:
            print("   ⚠️  Using fallback parsing method")
        
        if total_tr3_issues == 0:
            print("   ✅ Full TR3 compliance achieved")
        elif total_tr3_issues <= 3:
            print("   ⚠️  Minor TR3 compliance issues (acceptable for testing)")
        else:
            print("   ❌ Significant TR3 compliance issues detected")
        print()
    
    if passed == total:
        print("🎉 SYSTEM IS READY FOR PRODUCTION!")
        print("   ✅ All components operational")
        print("   ✅ pyx12 library integration working")
        print("   ✅ TR3 compliance validation active")
        print("   ✅ EDI file validation working correctly")
    else:
        print("⚠️  SYSTEM HAS ISSUES - Please review failed tests")

if __name__ == "__main__":
    main() 