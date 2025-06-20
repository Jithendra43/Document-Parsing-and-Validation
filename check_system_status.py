#!/usr/bin/env python3
"""
Comprehensive system status checker for EDI X12 278 processing system.
"""
import os
import sys
import requests
import json
from pathlib import Path

def check_environment():
    """Check environment configuration."""
    print("🔍 Checking Environment Configuration...")
    
    # Check .env file
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file exists")
        try:
            with open(".env", "r", encoding="utf-8") as f:
                content = f.read()
                print(f"   Content preview: {content[:100]}...")
        except Exception as e:
            print(f"❌ .env file read error: {e}")
    else:
        print("❌ .env file missing")
    
    # Check Python dependencies
    print("\n🔍 Checking Python Dependencies...")
    required_packages = [
        "fastapi", "uvicorn", "streamlit", "plotly", "groq", 
        "pydantic", "pydantic-settings", "structlog"
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} installed")
        except ImportError:
            print(f"❌ {package} missing")

def check_api_status():
    """Check API server status."""
    print("\n🔍 Checking API Server Status...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ API Server: RUNNING")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Components: {data.get('components', {})}")
        else:
            print(f"⚠️ API Server: ERROR (Status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("❌ API Server: NOT RUNNING")
    except Exception as e:
        print(f"❌ API Server: ERROR ({str(e)})")

def check_groq_api():
    """Check Groq API configuration and status."""
    print("\n🔍 Checking Groq API Configuration...")
    
    # Check environment variable
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        if groq_key == "gsk_REPLACE_WITH_YOUR_GROQ_API_KEY_HERE":
            print("⚠️ Groq API Key: PLACEHOLDER (needs real key)")
        elif groq_key.startswith("gsk_"):
            print("✅ Groq API Key: CONFIGURED")
            # Test API call
            try:
                import groq
                client = groq.Groq(api_key=groq_key)
                # Simple test call
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": "Test"}],
                    model="llama-3.1-8b-instant",
                    max_tokens=10
                )
                print("✅ Groq API: WORKING")
            except Exception as e:
                if "401" in str(e) or "Invalid API Key" in str(e):
                    print("❌ Groq API: INVALID API KEY")
                elif "429" in str(e) or "rate limit" in str(e).lower():
                    print("⚠️ Groq API: RATE LIMITED")
                    print("   Solution: Wait or get a new API key")
                else:
                    print(f"❌ Groq API: ERROR ({str(e)})")
        else:
            print("❌ Groq API Key: INVALID FORMAT")
    else:
        print("❌ Groq API Key: NOT SET")

def check_streamlit_status():
    """Check Streamlit server status."""
    print("\n🔍 Checking Streamlit Server Status...")
    
    try:
        response = requests.get("http://localhost:8501", timeout=5)
        if response.status_code == 200:
            print("✅ Streamlit Server: RUNNING")
        else:
            print(f"⚠️ Streamlit Server: ERROR (Status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("❌ Streamlit Server: NOT RUNNING")
    except Exception as e:
        print(f"❌ Streamlit Server: ERROR ({str(e)})")

def test_edi_processing():
    """Test basic EDI processing functionality."""
    print("\n🔍 Testing EDI Processing...")
    
    try:
        # Simple validation test
        test_data = {
            "content": "ISA*00*          *00*          *ZZ*SENDER_ID     *ZZ*RECEIVER_ID   *250620*1909*U*00501*000000001*0*P*>~GS*HS*SENDER_ID*RECEIVER_ID*20250620*1909*1*X*005010X217~ST*278*0001~SE*3*0001~GE*1*1~IEA*1*000000001~",
            "filename": "test.edi",
            "enable_ai_analysis": False  # Disable AI to avoid rate limits
        }
        
        response = requests.post(
            "http://localhost:8000/validate",
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ EDI Processing: WORKING")
            print(f"   Validation result: {result.get('is_valid', 'unknown')}")
        else:
            print(f"❌ EDI Processing: ERROR (Status: {response.status_code})")
            
    except Exception as e:
        print(f"❌ EDI Processing: ERROR ({str(e)})")

def show_rate_limit_solutions():
    """Show solutions for rate limiting issues."""
    print("\n💡 Solutions for Rate Limiting:")
    print("1. Wait 24 hours for rate limit reset")
    print("2. Get a new Groq API key from https://console.groq.com/keys")
    print("3. Upgrade to Groq Pro for higher limits")
    print("4. Use a different model (llama-3.1-8b-instant has highest free limits)")
    print("5. Disable AI analysis temporarily in the UI")

def main():
    """Run comprehensive system check."""
    print("🚀 EDI X12 278 System Status Checker")
    print("=" * 50)
    
    check_environment()
    check_api_status()
    check_groq_api()
    check_streamlit_status()
    test_edi_processing()
    
    print("\n" + "=" * 50)
    show_rate_limit_solutions()
    
    print("\n✅ System check completed!")
    print("📝 Review the results above to identify and fix any issues.")

if __name__ == "__main__":
    main() 