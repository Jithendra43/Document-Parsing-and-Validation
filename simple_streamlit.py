"""Simplified Streamlit app for testing - minimal imports."""

import streamlit as st
import os
import sys

# Page config
st.set_page_config(
    page_title="EDI X12 278 Processor - Test",
    page_icon="🏥",
    layout="wide"
)

def main():
    """Simplified main app for testing."""
    
    st.title("🏥 EDI X12 278 Processor - Test Version")
    st.markdown("**Testing minimal Streamlit functionality**")
    
    # Show system info
    st.subheader("System Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Python Version:**", sys.version[:10])
        st.write("**Streamlit Version:**", st.__version__)
        st.write("**Current Directory:**", os.getcwd())
    
    with col2:
        st.write("**Python Path:**")
        for path in sys.path[:5]:  # Show first 5 paths
            st.write(f"- {path}")
    
    # Test basic functionality
    st.subheader("Basic Tests")
    
    # Test 1: File uploader
    st.write("**Test 1: File Upload**")
    uploaded_file = st.file_uploader("Choose an EDI file", type=['edi', 'txt', 'x12'])
    if uploaded_file:
        st.success(f"✅ File uploaded: {uploaded_file.name}")
        content = uploaded_file.read().decode('utf-8')
        st.text_area("File Content (first 500 chars)", content[:500])
    
    # Test 2: Import testing
    st.write("**Test 2: Import Testing**")
    
    imports_to_test = [
        ("os", "import os"),
        ("sys", "import sys"),
        ("json", "import json"),
        ("pandas", "import pandas as pd"), 
        ("requests", "import requests"),
        ("pydantic", "from pydantic import BaseModel"),
        ("pydantic_settings", "from pydantic_settings import BaseSettings"),
        ("structlog", "import structlog"),
        ("groq", "import groq"),
    ]
    
    for name, import_stmt in imports_to_test:
        try:
            exec(import_stmt)
            st.write(f"✅ {name}: OK")
        except ImportError as e:
            st.write(f"❌ {name}: FAILED - {str(e)}")
        except Exception as e:
            st.write(f"⚠️ {name}: ERROR - {str(e)}")
    
    # Test 3: App imports
    st.write("**Test 3: App Module Imports**")
    
    app_imports = [
        ("app.config", "from app.config import settings"),
        ("app.core.logger", "from app.core.logger import get_logger"),
        ("app.core.models", "from app.core.models import EDIHeader"),
        ("app.core.edi_parser", "from app.core.edi_parser import EDI278Parser"),
    ]
    
    for name, import_stmt in app_imports:
        try:
            exec(import_stmt)
            st.write(f"✅ {name}: OK")
        except ImportError as e:
            st.write(f"❌ {name}: IMPORT FAILED - {str(e)}")
        except Exception as e:
            st.write(f"⚠️ {name}: ERROR - {str(e)}")
    
    # Test 4: Simple EDI processing
    st.write("**Test 4: Sample EDI Content**")
    
    sample_edi = st.text_area("Enter sample EDI content:", 
        value="ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *230101*1200*U*00501*000000001*0*P*>~")
    
    if st.button("Test Parse"):
        if sample_edi.strip():
            # Simple parsing test
            lines = sample_edi.strip().split('~')
            st.write(f"Found {len(lines)} segments:")
            for i, line in enumerate(lines[:5]):  # Show first 5
                if line.strip():
                    parts = line.split('*')
                    st.write(f"Segment {i+1}: {parts[0]} ({len(parts)-1} elements)")
        else:
            st.warning("Please enter some EDI content")
    
    # Instructions
    st.subheader("Next Steps")
    st.markdown("""
    **If this simplified version works:**
    1. Install missing dependencies: `pip install pydantic-settings structlog groq`
    2. Try running the full app: `streamlit run app.py`
    
    **If this fails:**
    1. Check Python version compatibility
    2. Reinstall Streamlit: `pip install --upgrade streamlit`
    3. Check for conflicting packages
    """)

if __name__ == "__main__":
    main() 