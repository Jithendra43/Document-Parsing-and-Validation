#!/usr/bin/env python3
"""
Test script to verify that all the critical fixes are working properly.
"""
import requests
import json
import time

def test_api_health():
    """Test API health endpoint."""
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ API Health Check: PASSED")
            print(f"   Status: {data.get('status')}")
            print(f"   Components: {data.get('components')}")
            return True
        else:
            print(f"❌ API Health Check: FAILED (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ API Health Check: FAILED ({str(e)})")
        return False

def test_validation():
    """Test EDI validation endpoint."""
    sample_edi = """ISA*00*          *00*          *ZZ*SENDER_ID     *ZZ*RECEIVER_ID   *250620*1909*U*00501*000000001*0*P*>~GS*HS*SENDER_ID*RECEIVER_ID*20250620*1909*1*X*005010X217~ST*278*0001~BHT*0078*13*10001234*20250620*1909~HL*1**20*1~NM1*PR*2*INSURANCE COMPANY*****PI*12345~TRN*1*93175-012547*9877281234~HL*2*1*21*1~NM1*1P*1*SMITH*JOHN****SV*123456789~HL*3*2*22*0~TRN*2*93175-012547*9877281234~NM1*IL*1*DOE*JANE*A***MI*987654321~DMG*D8*19850101*F~SE*12*0001~GE*1*1~IEA*1*000000001~"""
    
    try:
        data = {
            "content": sample_edi,
            "filename": "test.edi",
            "enable_ai_analysis": True
        }
        
        response = requests.post(
            "http://localhost:8000/validate",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ EDI Validation: PASSED")
            print(f"   Segments parsed: {result.get('segments_parsed', 0)}")
            print(f"   Validation status: {'Valid' if result.get('is_valid') else 'Invalid'}")
            print(f"   Issues found: {len(result.get('issues', []))}")
            return True
        else:
            print(f"❌ EDI Validation: FAILED (Status: {response.status_code})")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ EDI Validation: FAILED ({str(e)})")
        return False

def test_processing():
    """Test EDI processing endpoint."""
    sample_edi = """ISA*00*          *00*          *ZZ*SENDER_ID     *ZZ*RECEIVER_ID   *250620*1909*U*00501*000000001*0*P*>~GS*HS*SENDER_ID*RECEIVER_ID*20250620*1909*1*X*005010X217~ST*278*0001~BHT*0078*13*10001234*20250620*1909~HL*1**20*1~NM1*PR*2*INSURANCE COMPANY*****PI*12345~TRN*1*93175-012547*9877281234~HL*2*1*21*1~NM1*1P*1*SMITH*JOHN****SV*123456789~HL*3*2*22*0~TRN*2*93175-012547*9877281234~NM1*IL*1*DOE*JANE*A***MI*987654321~DMG*D8*19850101*F~SE*12*0001~GE*1*1~IEA*1*000000001~"""
    
    try:
        data = {
            "content": sample_edi,
            "filename": "test_processing.edi",
            "validate_only": False,
            "enable_ai_analysis": True,
            "output_format": "json"
        }
        
        response = requests.post(
            "http://localhost:8000/process",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get("job_id")
            print("✅ EDI Processing: PASSED")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {result.get('status')}")
            
            # Wait a moment for processing
            time.sleep(2)
            
            # Check job status
            job_response = requests.get(f"http://localhost:8000/jobs/{job_id}")
            if job_response.status_code == 200:
                job_data = job_response.json()
                print(f"   Final Status: {job_data.get('status')}")
                
                # Test JSON export
                export_response = requests.get(f"http://localhost:8000/jobs/{job_id}/export/json")
                if export_response.status_code == 200:
                    print("✅ JSON Export: PASSED")
                    export_data = export_response.json()
                    print(f"   Export size: {len(json.dumps(export_data))} bytes")
                else:
                    print(f"❌ JSON Export: FAILED (Status: {export_response.status_code})")
                
                return True
            else:
                print(f"❌ Job Status Check: FAILED (Status: {job_response.status_code})")
                return False
        else:
            print(f"❌ EDI Processing: FAILED (Status: {response.status_code})")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ EDI Processing: FAILED ({str(e)})")
        return False

def test_streamlit_connection():
    """Test if Streamlit is running."""
    try:
        response = requests.get("http://localhost:8501", timeout=5)
        if response.status_code == 200:
            print("✅ Streamlit Connection: PASSED")
            print("   Streamlit frontend is running")
            return True
        else:
            print(f"❌ Streamlit Connection: FAILED (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Streamlit Connection: FAILED ({str(e)})")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing EDI X12 278 Processing System")
    print("=" * 50)
    
    tests = [
        ("API Health Check", test_api_health),
        ("EDI Validation", test_validation),
        ("EDI Processing", test_processing),
        ("Streamlit Frontend", test_streamlit_connection)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is working correctly.")
    elif passed >= total * 0.75:
        print("⚠️ Most tests passed. System is mostly functional.")
    else:
        print("❌ Multiple test failures. System needs attention.")
    
    print("\n📋 Quick System Status:")
    print("   - API Server: http://localhost:8000")
    print("   - Streamlit Frontend: http://localhost:8501") 
    print("   - Health Check: http://localhost:8000/health")

if __name__ == "__main__":
    main() 