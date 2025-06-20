#!/usr/bin/env python3
"""
Comprehensive Groq API test script for EDI X12 278 system.
Tests all AI features and provides detailed diagnostic information.
"""

import os
import sys
import asyncio
import json
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_groq_installation():
    """Test if Groq library is properly installed."""
    print("🔍 Testing Groq Installation...")
    try:
        import groq
        print("✅ Groq library installed successfully")
        print(f"   Version: {getattr(groq, '__version__', 'unknown')}")
        return True
    except ImportError as e:
        print(f"❌ Groq library not installed: {e}")
        print("   Fix: pip install groq")
        return False

def test_environment_config():
    """Test environment configuration."""
    print("\n🔍 Testing Environment Configuration...")
    
    # Check for .env file
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file exists")
        
        # Read and check content
        try:
            with open(".env", "r") as f:
                content = f.read()
                if "GROQ_API_KEY" in content:
                    print("✅ GROQ_API_KEY found in .env file")
                    # Check if it's a placeholder
                    if "your_groq_api_key_here" in content:
                        print("⚠️  GROQ_API_KEY appears to be a placeholder")
                        print("   Please update with your actual Groq API key")
                        return False
                else:
                    print("❌ GROQ_API_KEY not found in .env file")
                    return False
        except Exception as e:
            print(f"❌ Error reading .env file: {e}")
            return False
    else:
        print("❌ .env file not found")
        print("   Please create .env file with GROQ_API_KEY")
        return False
    
    # Check environment variable
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        if api_key.startswith("gsk_"):
            print("✅ GROQ_API_KEY environment variable is properly formatted")
            print(f"   Key starts with: {api_key[:10]}...")
            return True
        else:
            print("❌ GROQ_API_KEY doesn't start with 'gsk_'")
            print("   Please check your API key format")
            return False
    else:
        print("❌ GROQ_API_KEY environment variable not set")
        return False

def test_direct_groq_api():
    """Test direct Groq API connection."""
    print("\n🔍 Testing Direct Groq API Connection...")
    
    try:
        from groq import Groq
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            print("❌ No API key available for testing")
            return False
        
        client = Groq(api_key=api_key)
        
        # Test simple API call
        print("   Making test API call...")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello, EDI system test successful!'"}
            ],
            max_tokens=50,
            temperature=0.1
        )
        
        message = response.choices[0].message.content
        print("✅ Direct Groq API call successful")
        print(f"   Response: {message[:50]}...")
        return True
        
    except Exception as e:
        error_str = str(e).lower()
        if "401" in error_str or "invalid" in error_str:
            print("❌ Invalid API key - please check your Groq API key")
        elif "429" in error_str or "rate limit" in error_str:
            print("⚠️ Rate limit exceeded - wait a moment and try again")
        elif "quota" in error_str:
            print("⚠️ API quota exceeded - consider upgrading your Groq plan")
        else:
            print(f"❌ API call failed: {e}")
        return False

def test_ai_analyzer():
    """Test the AI analyzer initialization."""
    print("\n🔍 Testing AI Analyzer Initialization...")
    
    try:
        from app.ai.analyzer import EDIAIAnalyzer
        
        analyzer = EDIAIAnalyzer()
        
        if analyzer.is_available:
            print("✅ AI Analyzer initialized successfully")
            print(f"   Model: {analyzer.model}")
            print(f"   Available: {analyzer.is_available}")
            return True
        else:
            print("❌ AI Analyzer not available")
            print("   Check Groq API key configuration")
            return False
            
    except Exception as e:
        print(f"❌ AI Analyzer initialization failed: {e}")
        return False

async def test_ai_analysis():
    """Test AI analysis functionality."""
    print("\n🔍 Testing AI Analysis Functionality...")
    
    try:
        from app.ai.analyzer import EDIAIAnalyzer
        from app.core.models import ParsedEDI, EDIHeader, EDISegment, ValidationResult
        from datetime import datetime
        
        analyzer = EDIAIAnalyzer()
        
        if not analyzer.is_available:
            print("❌ AI Analyzer not available for testing")
            return False
        
        # Create test data
        header = EDIHeader(
            isa_control_number="000000001",
            gs_control_number="1",
            st_control_number="0001",
            transaction_type="278",
            version="005010X279A1",
            sender_id="TEST_SENDER",
            receiver_id="TEST_RECEIVER"
        )
        
        segments = [
            EDISegment(segment_id="ISA", elements=["00", "          ", "00", "          "], position=1),
            EDISegment(segment_id="GS", elements=["HS", "SENDER", "RECEIVER"], position=2),
            EDISegment(segment_id="ST", elements=["278", "0001"], position=3),
            EDISegment(segment_id="BHT", elements=["0078", "00", "TEST123"], position=4),
            EDISegment(segment_id="SE", elements=["5", "0001"], position=5)
        ]
        
        parsed_edi = ParsedEDI(
            header=header,
            segments=segments,
            raw_content="TEST EDI CONTENT",
            file_size=100
        )
        
        validation_result = ValidationResult(
            is_valid=True,
            issues=[],
            segments_validated=5,
            validation_time=0.1,
            tr3_compliance=True,
            suggested_improvements=[]
        )
        
        print("   Running AI analysis...")
        analysis = await analyzer.analyze_edi(parsed_edi, validation_result)
        
        print("✅ AI Analysis completed successfully")
        print(f"   Confidence Score: {analysis.confidence_score:.2f}")
        print(f"   Risk Assessment: {analysis.risk_assessment}")
        print(f"   Anomalies Found: {len(analysis.anomalies_detected)}")
        print(f"   Suggestions: {len(analysis.suggested_fixes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI Analysis test failed: {e}")
        return False

def test_processing_service():
    """Test the main processing service."""
    print("\n🔍 Testing Processing Service...")
    
    try:
        from app.services.processor import EDIProcessingService
        
        service = EDIProcessingService()
        
        print("✅ Processing Service initialized successfully")
        print(f"   AI Available: {service.ai_analyzer.is_available}")
        print(f"   Smart Validator: {'enabled' if service.smart_validator else 'disabled'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Processing Service test failed: {e}")
        return False

async def test_end_to_end():
    """Test end-to-end processing with AI."""
    print("\n🔍 Testing End-to-End Processing...")
    
    try:
        from app.services.processor import EDIProcessingService
        from app.core.models import EDIFileUpload
        
        service = EDIProcessingService()
        
        # Fixed test content with properly formatted ISA segment for pyx12 compatibility
        test_content = """ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *250620*1909*U*00501*000000001*0*P*>~GS*HS*SENDER*RECEIVER*20250620*1909*1*X*005010X279A1~ST*278*0001~BHT*0078*00*TEST123*20250620*1909~HL*1**20*1~NM1*PR*2*TEST INSURANCE*****XX*1234567890~HL*2*1*21*1~NM1*82*1*DOCTOR*LASTNAME***XX*9876543210~HL*3*2*22*0~NM1*IL*1*PATIENT*LASTNAME***MI*123456789~DMG*D8*19800101*M~SE*12*0001~GE*1*1~IEA*1*000000001~"""
        
        upload_request = EDIFileUpload(
            filename="test_perfect.edi",
            content_type="text/plain",
            validate_only=False,
            enable_ai_analysis=True,
            output_format="json"
        )
        
        print("   Processing properly formatted EDI content...")
        job = await service.process_content(test_content, upload_request)
        
        if job.status.value == "completed":
            print("✅ End-to-end processing successful")
            print(f"   Job ID: {job.job_id}")
            print(f"   Processing Time: {job.processing_time:.2f}s")
            print(f"   Validation: {'passed' if job.validation_result.is_valid else 'failed'}")
            print(f"   FHIR Mapping: {'success' if job.fhir_mapping else 'failed'}")
            print(f"   AI Analysis: {'success' if job.ai_analysis else 'not available'}")
            
            if job.ai_analysis:
                print(f"     - Confidence: {job.ai_analysis.confidence_score:.2f}")
                print(f"     - Risk: {job.ai_analysis.risk_assessment}")
                print(f"     - Anomalies: {len(job.ai_analysis.anomalies_detected)}")
                print(f"     - Suggestions: {len(job.ai_analysis.suggested_fixes)}")
            
            return True
        else:
            print(f"❌ Processing failed: {job.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        return False

async def test_perfect_system():
    """Test the complete system with perfect EDI content to ensure all fixes work."""
    print("\n🎯 Testing Perfect System Configuration...")
    
    try:
        from app.services.processor import EDIProcessingService
        from app.core.models import EDIFileUpload
        
        service = EDIProcessingService()
        
        # Perfect EDI content that should parse flawlessly with pyx12
        perfect_content = """ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *250620*1909*U*00501*000000001*0*P*>~GS*HS*SENDER*RECEIVER*20250620*1909*1*X*005010X279A1~ST*278*0001~BHT*0078*00*PERFECT123*20250620*1909~HL*1**20*1~NM1*PR*2*PERFECT INSURANCE*****XX*1234567890~HL*2*1*21*1~NM1*82*1*PERFECT*DOCTOR***XX*9876543210~HL*3*2*22*0~NM1*IL*1*PERFECT*PATIENT***MI*123456789~DMG*D8*19900101*M~REF*1W*MEMBER123456~DTP*291*D8*20250620~UM*HS*99213*OFFICE VISIT~DTP*472*RD8*20250625-20250625~SE*14*0001~GE*1*1~IEA*1*000000001~"""
        
        upload_request = EDIFileUpload(
            filename="perfect_test.edi",
            content_type="text/plain",
            validate_only=False,
            enable_ai_analysis=True,
            output_format="fhir"
        )
        
        print("   🔧 Processing perfect EDI content...")
        job = await service.process_content(perfect_content, upload_request)
        
        # Analyze results
        print("\n📊 Perfect System Test Results:")
        print("=" * 50)
        
        # Check processing status
        status_icon = "✅" if job.status.value == "completed" else "❌"
        print(f"{status_icon} Processing Status: {job.status.value}")
        
        if job.error_message:
            print(f"❌ Error: {job.error_message}")
            return False
        
        # Check parsing success
        if job.parsed_edi:
            print(f"✅ EDI Parsing: SUCCESS ({len(job.parsed_edi.segments)} segments)")
            print(f"   📝 Parsing Method: {job.parsed_edi.parsing_method}")
        else:
            print("❌ EDI Parsing: FAILED")
            return False
        
        # Check validation results
        if job.validation_result:
            validation_icon = "✅" if job.validation_result.is_valid else "⚠️"
            print(f"{validation_icon} Validation: {'PASSED' if job.validation_result.is_valid else 'ISSUES FOUND'}")
            print(f"   📋 Segments Validated: {job.validation_result.segments_validated}")
            print(f"   🔍 TR3 Compliance: {'✅ YES' if job.validation_result.tr3_compliance else '⚠️ NO'}")
            print(f"   ⚠️ Issues Found: {len(job.validation_result.issues)}")
            
            # Show issue breakdown
            if job.validation_result.issues:
                critical = sum(1 for i in job.validation_result.issues if i.level.value == "critical")
                errors = sum(1 for i in job.validation_result.issues if i.level.value == "error") 
                warnings = sum(1 for i in job.validation_result.issues if i.level.value == "warning")
                print(f"     - Critical: {critical}, Errors: {errors}, Warnings: {warnings}")
        else:
            print("❌ Validation: NO RESULTS")
            return False
        
        # Check FHIR mapping
        if job.fhir_mapping:
            print(f"✅ FHIR Mapping: SUCCESS ({len(job.fhir_mapping.resources)} resources)")
            print(f"   🏥 Resources Created: {', '.join([r.resource_type for r in job.fhir_mapping.resources])}")
        else:
            print("⚠️ FHIR Mapping: FAILED")
        
        # Check AI analysis
        if job.ai_analysis:
            confidence_icon = "🎯" if job.ai_analysis.confidence_score >= 0.7 else "⚠️"
            print(f"✅ AI Analysis: SUCCESS")
            print(f"   {confidence_icon} Confidence Score: {job.ai_analysis.confidence_score:.2f}")
            print(f"   📊 Risk Assessment: {job.ai_analysis.risk_assessment}")
            print(f"   🔍 Anomalies Detected: {len(job.ai_analysis.anomalies_detected)}")
            print(f"   💡 Suggestions: {len(job.ai_analysis.suggested_fixes)}")
        else:
            print("⚠️ AI Analysis: NOT AVAILABLE")
        
        # Performance metrics
        print(f"⚡ Processing Time: {job.processing_time:.2f}s")
        
        # Overall assessment
        print("\n🎯 Overall Assessment:")
        success_criteria = [
            job.status.value == "completed",
            job.parsed_edi is not None,
            job.validation_result is not None,
            job.validation_result.segments_validated > 0
        ]
        
        if job.ai_analysis:
            success_criteria.append(job.ai_analysis.confidence_score >= 0.7)
        
        if all(success_criteria):
            print("🎉 PERFECT! All systems working optimally!")
            print("✅ Ready for executive presentation!")
            return True
        else:
            print("⚠️ Some components need attention")
            return False
            
    except Exception as e:
        print(f"❌ Perfect system test failed: {e}")
        import traceback
        print(f"📋 Details: {traceback.format_exc()}")
        return False

def provide_solutions():
    """Provide solutions for common issues."""
    print("\n💡 Common Solutions:")
    print("1. Invalid API Key:")
    print("   - Get a new key from https://console.groq.com/keys")
    print("   - Update your .env file: GROQ_API_KEY=gsk_your_key_here")
    print("   - Restart the application")
    print()
    print("2. Rate Limit Exceeded:")
    print("   - Wait 60 seconds and try again")
    print("   - Consider upgrading your Groq plan")
    print("   - Temporarily disable AI analysis in the UI")
    print()
    print("3. Quota Exceeded:")
    print("   - Upgrade to Groq Pro plan")
    print("   - Get a new API key")
    print("   - Use AI analysis sparingly")
    print()
    print("4. Installation Issues:")
    print("   - pip install groq --upgrade")
    print("   - pip install -r requirements.txt")
    print("   - Check Python version (3.8+ required)")

async def main():
    """Main test function."""
    print("🚀 Groq API Comprehensive Test Suite")
    print("=" * 50)
    
    tests = [
        ("Groq Installation", test_groq_installation),
        ("Environment Config", test_environment_config),
        ("Direct API Call", test_direct_groq_api),
        ("AI Analyzer", test_ai_analyzer),
        ("Processing Service", test_processing_service),
    ]
    
    async_tests = [
        ("AI Analysis Function", test_ai_analysis),
        ("End-to-End Processing", test_end_to_end),
        ("Perfect System Test", test_perfect_system),
    ]
    
    results = []
    
    # Run synchronous tests
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Run async tests
    for test_name, test_func in async_tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your Groq AI integration is working perfectly!")
        print("🚀 Ready for presentation!")
    else:
        print("⚠️  Some tests failed. See solutions below:")
        provide_solutions()
    
    return passed == total

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run tests
    asyncio.run(main()) 