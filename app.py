"""Enhanced Streamlit frontend for EDI X12 278 Processing with cloud compatibility."""

import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import io
import os
import uuid
import asyncio
import sys
from typing import Dict, List, Optional, Any

# Add app directory to path for imports
if './app' not in sys.path:
    sys.path.insert(0, './app')

# Try to import local components for cloud-only mode
try:
    from app.core.edi_parser import EDI278Parser, EDI278Validator
    from app.core.fhir_mapper import X12To278FHIRMapper
    from app.ai.analyzer import EDIAIAnalyzer
    from app.services.processor import EDIProcessingService
    from app.config import settings
    HAS_LOCAL_PROCESSING = True
except ImportError as e:
    HAS_LOCAL_PROCESSING = False
    print(f"Local processing not available: {e}")

# Page config
st.set_page_config(
    page_title="EDI X12 278 Processor",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
SUPPORTED_FORMATS = [".edi", ".txt", ".x12"]

# Check deployment mode
IS_STREAMLIT_CLOUD = ("streamlit.io" in os.getenv("STREAMLIT_SERVER_ADDRESS", "") or 
                      "streamlit.app" in os.getenv("STREAMLIT_SERVER_ADDRESS", "") or
                      not os.getenv("API_BASE_URL"))

# Helper function for Pydantic v2 compatibility
def safe_model_dump(obj):
    """Safely convert Pydantic object to dict using model_dump or dict method."""
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    elif hasattr(obj, 'dict'):
        return obj.dict()
    elif isinstance(obj, dict):
        return obj
    else:
        return obj

# Initialize processing service for cloud mode
if IS_STREAMLIT_CLOUD and HAS_LOCAL_PROCESSING:
    try:
        processing_service = EDIProcessingService()
        st.session_state['processing_service'] = processing_service
    except Exception as e:
        processing_service = None
        print(f"Could not initialize processing service: {e}")
else:
    processing_service = None

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #c3e6cb;
    }
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #f5c6cb;
    }
    .warning-box {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #ffeeba;
    }
    .cloud-mode {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown('<h1 class="main-header">🏥 EDI X12 278 Processor</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center;"><strong>AI-powered EDI processing with FHIR mapping and validation</strong></p>', unsafe_allow_html=True)
    
    # Show deployment mode
    if IS_STREAMLIT_CLOUD:
        st.markdown('<div class="cloud-mode">☁️ <strong>Cloud Mode</strong> - Enhanced with embedded processing</div>', unsafe_allow_html=True)
    
    # Navigation
    st.sidebar.title("EDI X12 278 Processor")
    
    page = st.sidebar.selectbox(
        "Navigation",
        ["Home", "Upload & Process", "Validate Only", "Dashboard", "Job History", "Settings"]
    )
    
    # Check system health
    if not IS_STREAMLIT_CLOUD:
        health_status = check_api_health()
        if not health_status["healthy"]:
            st.error("⚠️ API service is unavailable. Switching to embedded processing mode.")
            st.session_state['force_embedded'] = True
    
    # Route to different pages
    if page == "Home":
        show_home_page()
    elif page == "Upload & Process":
        show_upload_page()
    elif page == "Validate Only":
        show_validation_page()
    elif page == "Dashboard":
        show_dashboard_page()
    elif page == "Job History":
        show_job_history_page()
    elif page == "Settings":
        show_settings_page()


def check_api_health():
    """Check if the API is healthy."""
    if IS_STREAMLIT_CLOUD:
        return {"healthy": True, "mode": "embedded"}
    
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return {"healthy": True, "data": response.json()}
        else:
            return {"healthy": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def show_home_page():
    """Show the home page with overview and getting started."""
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("Welcome to the EDI X12 278 Processor")
        
        st.markdown("""
        This application provides comprehensive processing of X12 278 (Prior Authorization) EDI transactions with:
        
        ✅ **Structural validation** against X12 standards  
        ✅ **TR3 compliance checking** for healthcare transactions  
        ✅ **AI-powered anomaly detection** using Groq/Llama 3  
        ✅ **FHIR mapping** to modern healthcare standards  
        ✅ **Real-time processing** with detailed reporting  
        ✅ **Cloud-native deployment** with embedded processing
        
        ### Getting Started
        1. Use **Upload & Process** to convert EDI files to FHIR
        2. Use **Validate Only** to check file compliance and TR3 standards
        3. Monitor progress in the **Dashboard**
        4. Review detailed results in **Job History**
        5. Download results in JSON, XML, or EDI formats
        """)
        
        # Feature highlights
        st.subheader("🎯 Key Features")
        features = [
            "📋 **Comprehensive Validation**: Full X12 278 structural validation with TR3 compliance checking",
            "🤖 **AI Analysis**: Advanced anomaly detection and intelligent suggestions using Groq/Llama 3",
            "🔄 **FHIR Mapping**: Convert X12 278 to FHIR CoverageEligibilityRequest resources",
            "📊 **Detailed Results**: Comprehensive tables with issue tracking and justifications",
            "💾 **Export Options**: Download results in JSON, XML, or EDI formats",
            "📈 **Analytics Dashboard**: Real-time monitoring and processing statistics"
        ]
        
        for feature in features:
            st.markdown(feature)
    
    with col2:
        st.subheader("System Status")
        
        if IS_STREAMLIT_CLOUD:
            st.success("☁️ Cloud Mode Active")
            st.info("✨ Enhanced with embedded processing")
            
            # Show available components
            st.markdown("**Available Components:**")
            if HAS_LOCAL_PROCESSING:
                st.write("✅ EDI Parser: Available")
                st.write("✅ Validator: Available") 
                st.write("✅ FHIR Mapper: Available")
                st.write("✅ AI Analyzer: Available")
            else:
                st.write("⚠️ Some components may be limited")
        else:
            health = check_api_health()
            
            if health["healthy"]:
                health_data = health.get("data", {})
                st.success("✅ System Healthy")
                
                st.markdown("**Components:**")
                components = health_data.get("components", {})
                for component, status in components.items():
                    icon = "✅" if status == "healthy" else "⚠️"
                    st.write(f"{icon} {component.title()}: {status}")
        
        # Quick links
        st.subheader("Quick Actions")
        if st.button("🚀 Process Sample File"):
            st.session_state['sample_demo'] = True
            st.rerun()
        
        if st.button("📖 View Documentation"):
            st.info("Documentation available in the repository README.md")


def show_upload_page():
    """Show the upload and processing page with enhanced features."""
    
    st.header("Process EDI Files")
    st.markdown("Upload your X12 278 EDI files for comprehensive processing and validation")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Choose an EDI file",
        type=["edi", "txt", "x12"],
        help="Upload X12 278 EDI files in .edi, .txt, or .x12 format"
    )
    
    # Processing options
    st.subheader("Processing Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        validate_only = st.checkbox("Validation Only", value=False, help="Only validate without conversion")
        enable_ai_analysis = st.checkbox("Enable AI Analysis", value=True, help="Use AI for enhanced analysis")
    
    with col2:
        output_format = st.selectbox(
            "Output Format",
            ["fhir", "json", "xml"],
            help="Choose the output format for processing results"
        )
    
    # Advanced options
    with st.expander("Advanced Options"):
        options = {
            'show_details': st.checkbox("Show Detailed Results", value=True),
            'export_results': st.checkbox("Enable Export Options", value=True),
            'tr3_validation': st.checkbox("Strict TR3 Validation", value=True),
            'include_warnings': st.checkbox("Include Warnings", value=True)
        }
    
    # Process button
    if uploaded_file is not None:
        if st.button("Process File", type="primary"):
            # Use synchronous processing to avoid async issues
            process_uploaded_file_sync(uploaded_file, validate_only, enable_ai_analysis, output_format, options)
    
    # Demo section
    st.subheader("Try Demo")
    st.markdown("Test the system with sample EDI content")
    
    if st.button("Process Demo File"):
        demo_content = generate_sample_edi()
        process_demo_content(demo_content, validate_only, enable_ai_analysis, output_format)


def process_uploaded_file_sync(uploaded_file, validate_only, enable_ai_analysis, output_format, options=None):
    """Process the uploaded file synchronously."""
    
    options = options or {}
    
    # Show processing message
    with st.spinner("Processing file..."):
        try:
            # Read file content
            content = uploaded_file.read().decode('utf-8')
            
            # Choose processing method
            if IS_STREAMLIT_CLOUD or st.session_state.get('force_embedded', False):
                # Use embedded processing
                result = process_with_embedded_service_sync(content, uploaded_file.name, 
                                                           validate_only, enable_ai_analysis, 
                                                           output_format, options)
            else:
                # Use API processing
                result = process_with_api_sync(content, uploaded_file.name, 
                                              validate_only, enable_ai_analysis, 
                                              output_format)
            
            if result:
                display_processing_results(result, uploaded_file.name)
            else:
                st.error("Processing failed - no result returned")
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)


def process_with_embedded_service_sync(content, filename, validate_only, enable_ai_analysis, output_format, options):
    """Process using embedded service synchronously."""
    if not HAS_LOCAL_PROCESSING:
        st.error("Embedded processing not available")
        return None
    
    try:
        from app.core.models import EDIFileUpload
        from app.services.processor import EDIProcessingService
        
        # Create processing service
        processor = EDIProcessingService()
        
        # Create upload request
        upload_request = EDIFileUpload(
            filename=filename,
            content_type="text/plain",
            validate_only=validate_only,
            enable_ai_analysis=enable_ai_analysis,
            output_format=output_format
        )
        
        # Process content synchronously using asyncio
        import asyncio
        
        # Create new event loop if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Process content
        job = loop.run_until_complete(processor.process_content(content, upload_request))
        
        # Convert job to API-compatible format
        result = {
            "job_id": job.job_id,
            "status": job.status.value,
            "message": "Processing completed" if job.status.value == "completed" else "Processing failed"
        }
        
        # Store job in session state for later retrieval
        if 'jobs' not in st.session_state:
            st.session_state['jobs'] = {}
        st.session_state['jobs'][job.job_id] = job
        
        return result
        
    except Exception as e:
        st.error(f"Embedded processing failed: {str(e)}")
        return None


def process_with_api_sync(content, filename, validate_only, enable_ai_analysis, output_format):
    """Process using API synchronously."""
    try:
        # Prepare API request
        data = {
            "content": content,
            "filename": filename,
            "validate_only": validate_only,
            "enable_ai_analysis": enable_ai_analysis,
            "output_format": output_format
        }
        
        # Call API
        response = requests.post(f"{API_BASE_URL}/process", json=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API processing failed: {response.text}")
            return None
            
    except Exception as e:
        st.error(f"API call failed: {str(e)}")
        return None


def process_demo_content(content, validate_only, enable_ai_analysis, output_format):
    """Process demo content synchronously."""
    try:
        if IS_STREAMLIT_CLOUD or st.session_state.get('force_embedded', False):
            # Use embedded processing for demo
            result = process_with_embedded_service_sync(content, "demo_278.edi", validate_only, 
                                                       enable_ai_analysis, output_format, {})
            if result:
                display_processing_results(result, "demo_278.edi")
        else:
            # Use API processing for demo
            result = process_with_api_sync(content, "demo_278.edi", validate_only, 
                                          enable_ai_analysis, output_format)
            if result:
                display_processing_results(result, "demo_278.edi")
            else:
                st.info("Demo processing requires API or embedded mode")
    except Exception as e:
        st.error(f"Demo processing failed: {str(e)}")


async def process_with_embedded_service(content, filename, validate_only, enable_ai_analysis, output_format, options):
    """Process using embedded service."""
    if not HAS_LOCAL_PROCESSING:
        st.error("Embedded processing not available")
        return None
    
    try:
        from app.core.models import EDIFileUpload
        
        # Create upload request
        upload_request = EDIFileUpload(
            filename=filename,
            content_type="text/plain",
            validate_only=validate_only,
            enable_ai_analysis=enable_ai_analysis,
            output_format=output_format
        )
        
        # Process content
        job = await processing_service.process_content(content, upload_request)
        
        # Convert job to API-compatible format
        result = {
            "job_id": job.job_id,
            "status": job.status.value,
            "message": "Processing completed" if job.status.value == "completed" else "Processing failed"
        }
        
        # Store job in session state for later retrieval
        if 'jobs' not in st.session_state:
            st.session_state['jobs'] = {}
        st.session_state['jobs'][job.job_id] = job
        
        return result
        
    except Exception as e:
        st.error(f"Embedded processing failed: {str(e)}")
        return None


def display_processing_results(result, filename):
    """Display comprehensive processing results with all advanced features."""
    
    # Handle both dict and ProcessingJob objects
    if hasattr(result, 'model_dump') or hasattr(result, 'dict'):
        # Pydantic object
        job_id = result.job_id
        status = result.status
        job_details = result
    elif isinstance(result, dict):
        # Dictionary
        job_id = result.get("job_id")
        status = result.get("status", "unknown")
        job_details = result
    else:
        # Object with attributes
        job_id = getattr(result, 'job_id', None)
        status = getattr(result, 'status', 'unknown')
        job_details = result
    
    # Status display
    if status == "completed":
        st.success(f"Successfully processed {filename}")
    elif status == "failed":
        st.error(f"Processing failed for {filename}")
    else:
        st.info(f"Processing {status} for {filename}")
    
    # Get detailed job information if not already available
    if not job_details and job_id:
        if IS_STREAMLIT_CLOUD and job_id in st.session_state.get('jobs', {}):
            # Get from session state (embedded mode)
            job_details = st.session_state['jobs'][job_id]
        else:
            # Get from API
            try:
                job_response = requests.get(f"{API_BASE_URL}/jobs/{job_id}")
                if job_response.status_code == 200:
                    job_details = job_response.json()
            except Exception as e:
                st.warning(f"Could not fetch job details: {e}")
    
    if not job_details:
        st.warning("No detailed results available")
        st.info("This might be due to a processing error or expired job data.")
        
        # Show basic processing info if available
        if job_id:
            st.code(f"Job ID: {job_id}")
            st.code(f"Status: {status}")
            
            # Try to fetch results directly if we have a job_id
            if status == "completed":
                st.info("Attempting to retrieve processing results...")
                
                # Try different approaches to get results
                try:
                    if IS_STREAMLIT_CLOUD:
                        st.warning("Results not found in session. Try processing again.")
                    else:
                        st.warning("Could not connect to API for detailed results.")
                except:
                    pass
        return
    
    # Show error message if present
    if hasattr(job_details, 'error_message') and job_details.error_message:
        if "warnings" in job_details.error_message.lower():
            st.warning(f"Processing completed with warnings: {job_details.error_message}")
        else:
            st.error(f"Processing errors: {job_details.error_message}")
    
    # Show processing summary
    st.subheader("Processing Summary")
    
    # Create processing summary columns
    summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
    
    with summary_col1:
        st.metric("File", filename)
    with summary_col2:
        st.metric("Status", status.upper())
    with summary_col3:
        if hasattr(job_details, 'processing_time') or 'processing_time' in (job_details if isinstance(job_details, dict) else {}):
            processing_time = getattr(job_details, 'processing_time', None) or (job_details.get('processing_time') if isinstance(job_details, dict) else None)
            if processing_time:
                st.metric("Processing Time", f"{processing_time:.2f}s")
            else:
                st.metric("Processing Time", "N/A")
        else:
            st.metric("Processing Time", "N/A")
    with summary_col4:
        if hasattr(job_details, 'file_size') or 'file_size' in (job_details if isinstance(job_details, dict) else {}):
            file_size = getattr(job_details, 'file_size', None) or (job_details.get('file_size') if isinstance(job_details, dict) else None)
            if file_size:
                st.metric("File Size", f"{file_size:,} bytes")
            else:
                st.metric("File Size", "N/A")
        else:
            st.metric("File Size", "N/A")
    
    # Extract data from job_details (handle both dict and object)
    if hasattr(job_details, 'model_dump') or hasattr(job_details, 'dict'):
        # Pydantic object
        validation_result = getattr(job_details, 'validation_result', None)
        ai_analysis = getattr(job_details, 'ai_analysis', None)
        fhir_mapping = getattr(job_details, 'fhir_mapping', None)
        parsed_edi = getattr(job_details, 'parsed_edi', None)
    elif isinstance(job_details, dict):
        # Dictionary
        validation_result = job_details.get("validation_result")
        ai_analysis = job_details.get("ai_analysis")
        fhir_mapping = job_details.get("fhir_mapping")
        parsed_edi = job_details.get("parsed_edi")
    else:
        # Object with attributes
        validation_result = getattr(job_details, 'validation_result', None)
        ai_analysis = getattr(job_details, 'ai_analysis', None)
        fhir_mapping = getattr(job_details, 'fhir_mapping', None)
        parsed_edi = getattr(job_details, 'parsed_edi', None)
    
    # Show what results are available
    st.subheader("Available Results")
    result_cols = st.columns(4)
    
    with result_cols[0]:
        if validation_result:
            st.success("✓ Validation Results")
        else:
            st.error("✗ No Validation Results")
    
    with result_cols[1]:
        if ai_analysis:
            st.success("✓ AI Analysis")
        else:
            st.warning("⚠ No AI Analysis")
    
    with result_cols[2]:
        if fhir_mapping:
            st.success("✓ FHIR Mapping")
        else:
            st.error("✗ FHIR Mapping Failed")
    
    with result_cols[3]:
        if parsed_edi:
            st.success("✓ EDI Parsing")
        else:
            st.error("✗ EDI Parsing Failed")
    
    # Validation Results Section
    if validation_result:
        display_validation_section(validation_result, job_id)
    else:
        st.subheader("Validation Results")
        st.error("No validation results available. This usually indicates a parsing failure.")
        
        # Show some basic info if we have parsed EDI
        if parsed_edi:
            if hasattr(parsed_edi, 'segments') or (isinstance(parsed_edi, dict) and 'segments' in parsed_edi):
                segments = getattr(parsed_edi, 'segments', None) or parsed_edi.get('segments', [])
                st.info(f"Document contains {len(segments)} segments")
    
    # AI Analysis Section
    if ai_analysis:
        display_ai_analysis_section(ai_analysis)
    else:
        st.subheader("AI Analysis & Insights")
        st.warning("AI analysis not available. This may be due to API limits or processing errors.")
    
    # FHIR Mapping Section
    if fhir_mapping and status == "completed":
        display_fhir_section(fhir_mapping)
    elif status == "completed":
        st.subheader("FHIR Transformation")
        st.error("FHIR mapping failed")
        st.info("This is usually due to validation errors or missing required EDI segments.")
        
        # Show error details if available
        if hasattr(job_details, 'error_message') or (isinstance(job_details, dict) and 'error_message' in job_details):
            error_msg = getattr(job_details, 'error_message', None) or job_details.get('error_message')
            if error_msg and "fhir" in error_msg.lower():
                st.error(f"Error: {error_msg}")
    
    # Download Section - Always show if we have a job_id
    if job_id:
        display_download_section(job_id, filename, job_details)


def display_validation_section(validation_result, job_id):
    """Display comprehensive validation results."""
    st.subheader("Validation Results")
    
    # Extract validation data with error handling
    if hasattr(validation_result, 'model_dump') or hasattr(validation_result, 'dict'):
        val_data = safe_model_dump(validation_result)
    elif isinstance(validation_result, dict):
        val_data = validation_result
    else:
        val_data = {
            'is_valid': getattr(validation_result, 'is_valid', False),
            'tr3_compliance': getattr(validation_result, 'tr3_compliance', False),
            'segments_validated': getattr(validation_result, 'segments_validated', 0),
            'validation_time': getattr(validation_result, 'validation_time', 0),
            'issues': getattr(validation_result, 'issues', [])
        }
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        is_valid = val_data.get("is_valid", False)
        st.metric("Valid", "YES" if is_valid else "NO")
    
    with col2:
        tr3_compliance = val_data.get("tr3_compliance", False)
        st.metric("TR3 Compliant", "YES" if tr3_compliance else "NO")
    
    with col3:
        segments_validated = val_data.get("segments_validated", 0)
        st.metric("Segments", segments_validated)
    
    with col4:
        validation_time = val_data.get("validation_time", 0)
        st.metric("Time", f"{validation_time:.3f}s")
    
    # Issues table
    issues = val_data.get("issues", [])
    if issues:
        st.subheader(f"Validation Issues ({len(issues)} found)")
        
        # Convert issues to DataFrame
        if issues and (hasattr(issues[0], 'model_dump') or hasattr(issues[0], 'dict')):
            issues_data = [safe_model_dump(issue) for issue in issues]
        else:
            issues_data = issues
        
        issues_df = pd.DataFrame(issues_data)
        
        # Ensure required columns exist
        required_columns = ['level', 'code', 'message', 'segment', 'line_number', 'suggested_fix']
        for col in required_columns:
            if col not in issues_df.columns:
                issues_df[col] = 'N/A'
        
        # Filter controls
        col_filter1, col_filter2 = st.columns(2)
        
        with col_filter1:
            level_options = issues_df['level'].unique()
            level_filter = st.multiselect(
                "Filter by Severity",
                options=level_options,
                default=level_options,
                key=f"level_filter_{job_id}"
            )
        
        with col_filter2:
            segment_options = issues_df['segment'].unique()
            segment_filter = st.multiselect(
                "Filter by Segment",
                options=segment_options,
                default=segment_options,
                key=f"segment_filter_{job_id}"
            )
        
        # Apply filters
        filtered_df = issues_df[
            (issues_df['level'].isin(level_filter)) &
            (issues_df['segment'].isin(segment_filter))
        ]
        
        if not filtered_df.empty:
            # Display formatted table
            display_df = filtered_df[required_columns].copy()
            display_df.columns = ['Severity', 'Code', 'Message', 'Segment', 'Line #', 'Suggested Fix']
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Severity": st.column_config.TextColumn(width="small"),
                    "Code": st.column_config.TextColumn(width="small"),
                    "Message": st.column_config.TextColumn(width="large"),
                    "Segment": st.column_config.TextColumn(width="small"),
                    "Line #": st.column_config.TextColumn(width="small"),
                    "Suggested Fix": st.column_config.TextColumn(width="large")
                }
            )
            
            # Issue summary chart
            if len(filtered_df) > 0:
                level_counts = filtered_df['level'].value_counts()
                
                fig = px.bar(
                    x=level_counts.index,
                    y=level_counts.values,
                    title="Issues by Severity Level",
                    color=level_counts.index,
                    color_discrete_map={
                        'critical': '#ff4444',
                        'error': '#ff8800',
                        'warning': '#ffcc00', 
                        'info': '#4488ff'
                    }
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No issues match the selected filters.")
    else:
        st.success("No validation issues found! Document is fully compliant.")


def display_ai_analysis_section(ai_analysis):
    """Display AI analysis results."""
    st.subheader("AI Analysis & Insights")
    
    # Extract AI data
    if hasattr(ai_analysis, 'dict'):
        ai_data = ai_analysis.dict()
    elif isinstance(ai_analysis, dict):
        ai_data = ai_analysis
    else:
        ai_data = {
            'confidence_score': getattr(ai_analysis, 'confidence_score', 0),
            'risk_assessment': getattr(ai_analysis, 'risk_assessment', 'unknown'),
            'anomalies_detected': getattr(ai_analysis, 'anomalies_detected', []),
            'suggested_fixes': getattr(ai_analysis, 'suggested_fixes', [])
        }
    
    # AI metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        confidence_score = ai_data.get('confidence_score', 0)
        confidence_color = "green" if confidence_score >= 0.8 else "orange" if confidence_score >= 0.6 else "red"
        st.metric("Confidence Score", f"{confidence_score:.2f}", delta=None)
    
    with col2:
        risk_level = ai_data.get('risk_assessment', 'unknown').upper()
        risk_color = "green" if risk_level == "LOW" else "orange" if risk_level == "MEDIUM" else "red"
        st.metric("Risk Level", risk_level)
    
    with col3:
        anomalies = ai_data.get("anomalies_detected", [])
        st.metric("Anomalies", len(anomalies))
    
    # Anomalies display
    if anomalies:
        st.write("**Detected Anomalies:**")
        for i, anomaly in enumerate(anomalies, 1):
            st.warning(f"{i}. {anomaly}")
    
    # AI suggestions
    suggestions = ai_data.get("suggested_fixes", [])
    if suggestions:
        st.write("**AI Recommendations:**")
        for i, suggestion in enumerate(suggestions, 1):
            st.info(f"{i}. {suggestion}")


def display_fhir_section(fhir_mapping):
    """Display FHIR mapping results."""
    st.subheader("FHIR Mapping Results")
    
    # Extract FHIR data
    if hasattr(fhir_mapping, 'dict'):
        fhir_data = fhir_mapping.dict()
    elif isinstance(fhir_mapping, dict):
        fhir_data = fhir_mapping
    else:
        fhir_data = {
            'resources': getattr(fhir_mapping, 'resources', []),
            'resource_count': getattr(fhir_mapping, 'resource_count', 0)
        }
    
    resources = fhir_data.get('resources', [])
    
    if resources:
        st.success(f"Successfully mapped to {len(resources)} FHIR resources")
        
        # Resource summary
        resource_types = {}
        for resource in resources:
            if hasattr(resource, 'dict'):
                res_data = resource.dict()
            else:
                res_data = resource
            
            res_type = res_data.get('resource_type', 'Unknown')
            resource_types[res_type] = resource_types.get(res_type, 0) + 1
        
        # Display resource counts
        cols = st.columns(len(resource_types))
        for i, (res_type, count) in enumerate(resource_types.items()):
            with cols[i]:
                st.metric(f"Resources of Type {res_type}", count)
        
        # Detailed resource view
        with st.expander("🔍 View FHIR Resources"):
            for i, resource in enumerate(resources):
                if hasattr(resource, 'dict'):
                    res_data = resource.dict()
                else:
                    res_data = resource
                
                st.subheader(f"{res_data.get('resource_type', 'Unknown')} Resource")
                st.json(res_data.get('data', {}))
    else:
        st.warning("No FHIR resources were generated")


def display_download_section(job_id, filename, job_details):
    """Display download options for all formats."""
    st.subheader("Download Results")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Extract data from job_details (handle both dict and object)
    if hasattr(job_details, 'dict') or hasattr(job_details, 'model_dump'):
        # Pydantic object
        job_dict = safe_model_dump(job_details)
        fhir_mapping = getattr(job_details, 'fhir_mapping', None)
        parsed_edi = getattr(job_details, 'parsed_edi', None)
        validation_result = getattr(job_details, 'validation_result', None)
    elif isinstance(job_details, dict):
        # Dictionary
        job_dict = job_details
        fhir_mapping = job_details.get('fhir_mapping')
        parsed_edi = job_details.get('parsed_edi')
        validation_result = job_details.get('validation_result')
    else:
        # Object with attributes
        job_dict = {
            'job_id': getattr(job_details, 'job_id', job_id),
            'filename': getattr(job_details, 'filename', filename),
            'status': getattr(job_details, 'status', 'unknown')
        }
        fhir_mapping = getattr(job_details, 'fhir_mapping', None)
        parsed_edi = getattr(job_details, 'parsed_edi', None)
        validation_result = getattr(job_details, 'validation_result', None)
    
    # JSON Download
    with col1:
        try:
            if IS_STREAMLIT_CLOUD:
                # Generate JSON from job details
                json_content = json.dumps(job_dict, indent=2, default=str)
                st.download_button(
                    "JSON",
                    json_content,
                    f"result_{filename}.json",
                    "application/json",
                    key=f"json_{job_id}",
                    help="Download complete processing results as JSON"
                )
            else:
                response = requests.get(f"{API_BASE_URL}/jobs/{job_id}/export/json")
                if response.status_code == 200:
                    st.download_button(
                        "JSON",
                        response.text,
                        f"result_{filename}.json",
                        "application/json",
                        key=f"json_{job_id}",
                        help="Download complete processing results as JSON"
                    )
                else:
                    st.button("JSON", disabled=True, help="JSON export not available")
        except Exception:
            st.button("JSON", disabled=True, help="JSON export failed")
    
    # FHIR Download
    with col2:
        try:
            if fhir_mapping:
                if IS_STREAMLIT_CLOUD:
                    # Generate FHIR JSON from mapping
                    fhir_content = json.dumps(safe_model_dump(fhir_mapping), indent=2, default=str)
                    st.download_button(
                        "FHIR",
                        fhir_content,
                        f"fhir_{filename}.json",
                        "application/fhir+json",
                        key=f"fhir_{job_id}",
                        help="Download FHIR resources as JSON"
                    )
                else:
                    response = requests.get(f"{API_BASE_URL}/jobs/{job_id}/export/xml")
                    if response.status_code == 200:
                        st.download_button(
                            "FHIR",
                            response.text,
                            f"fhir_{filename}.xml",
                            "application/fhir+xml",
                            key=f"fhir_{job_id}",
                            help="Download FHIR resources as XML"
                        )
                    else:
                        st.button("FHIR", disabled=True, help="FHIR export not available")
            else:
                st.button("FHIR", disabled=True, help="No FHIR mapping available")
        except Exception:
            st.button("FHIR", disabled=True, help="FHIR export failed")
    
    # EDI Download
    with col3:
        try:
            if parsed_edi:
                if IS_STREAMLIT_CLOUD:
                    # Generate EDI content from parsed data
                    if hasattr(parsed_edi, 'raw_content'):
                        edi_content = parsed_edi.raw_content
                    elif isinstance(parsed_edi, dict) and 'raw_content' in parsed_edi:
                        edi_content = parsed_edi['raw_content']
                    else:
                        edi_content = "EDI content not available"
                        
                    st.download_button(
                        "EDI",
                        edi_content,
                        f"processed_{filename}",
                        "text/plain",
                        key=f"edi_{job_id}",
                        help="Download original EDI content"
                    )
                else:
                    response = requests.get(f"{API_BASE_URL}/jobs/{job_id}/export/edi")
                    if response.status_code == 200:
                        st.download_button(
                            "EDI",
                            response.text,
                            f"processed_{filename}",
                            "text/plain",
                            key=f"edi_{job_id}",
                            help="Download processed EDI content"
                        )
                    else:
                        st.button("EDI", disabled=True, help="EDI export not available")
            else:
                st.button("EDI", disabled=True, help="No EDI data available")
        except Exception:
            st.button("EDI", disabled=True, help="EDI export failed")
    
    # Validation Report Download
    with col4:
        try:
            if validation_result:
                if IS_STREAMLIT_CLOUD:
                    # Generate validation report
                    report_content = generate_validation_report(validation_result, filename)
                    st.download_button(
                        "Report",
                        report_content,
                        f"validation_{filename}.txt",
                        "text/plain",
                        key=f"report_{job_id}",
                        help="Download validation report"
                    )
                else:
                    response = requests.get(f"{API_BASE_URL}/jobs/{job_id}/export/validation")
                    if response.status_code == 200:
                        st.download_button(
                            "Report",
                            response.text,
                            f"validation_{filename}.json",
                            "application/json",
                            key=f"report_{job_id}",
                            help="Download validation report"
                        )
                    else:
                        st.button("Report", disabled=True, help="Report not available")
            else:
                st.button("Report", disabled=True, help="No validation data available")
        except Exception:
            st.button("Report", disabled=True, help="Report generation failed")
    
    # Additional download info
    with st.expander("Download Guide"):
        st.markdown("""
        **Download Options:**
        
        - **JSON:** Complete processing results in JSON format
        - **FHIR:** Healthcare data in FHIR format for interoperability  
        - **EDI:** Original or processed EDI X12 278 document
        - **Report:** Detailed validation and analysis report
        """)
    
    # Show helpful tips
    st.info("All downloads are formatted for easy import into other healthcare systems.")


def generate_validation_report(validation_result, filename):
    """Generate a comprehensive validation report."""
    report = f"""
EDI X12 278 VALIDATION REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
File: {filename}

VALIDATION SUMMARY
- Valid: {validation_result.is_valid}
- TR3 Compliant: {validation_result.tr3_compliance}
- Segments Validated: {validation_result.segments_validated}
- Validation Time: {validation_result.validation_time:.3f}s

"""
    
    if validation_result.issues:
        report += f"ISSUES FOUND ({len(validation_result.issues)}):\n"
        for i, issue in enumerate(validation_result.issues, 1):
            report += f"{i}. [{issue.level}] {issue.message}\n"
            if issue.segment:
                report += f"   Segment: {issue.segment}\n"
            if issue.suggested_fix:
                report += f"   Fix: {issue.suggested_fix}\n"
            report += "\n"
    
    if validation_result.suggested_improvements:
        report += "RECOMMENDATIONS:\n"
        for i, suggestion in enumerate(validation_result.suggested_improvements, 1):
            report += f"{i}. {suggestion}\n"
    
    return report


def show_validation_page():
    """Show the enhanced validation page with all features."""
    
    st.header("Validation & Analysis")
    st.markdown("Comprehensive validation with TR3 compliance checking and AI insights")
    
    # Text area for direct input
    st.subheader("Paste EDI Content")
    edi_content = st.text_area(
        "EDI Content",
        height=300,
        placeholder="Paste your X12 278 EDI content here...",
        help="Paste the complete EDI transaction including ISA, GS, ST segments"
    )
    
    # File upload option
    st.subheader("Or Upload File")
    uploaded_file = st.file_uploader(
        "Choose an EDI file for validation",
        type=['edi', 'txt', 'x12'],
        help="Upload an EDI file (max 50MB)"
    )
    
    # Use uploaded file content if available
    if uploaded_file:
        edi_content = uploaded_file.read().decode('utf-8')
        st.success(f"Loaded file: {uploaded_file.name}")
    
    # Validation options
    st.subheader("Validation Options")
    col1, col2 = st.columns(2)
    with col1:
        enable_ai_analysis = st.checkbox("Enable AI Analysis", value=True)
        strict_tr3 = st.checkbox("Strict TR3 Validation", value=False)
    
    with col2:
        show_details = st.checkbox("Show Detailed Metrics", value=True)
        export_results = st.checkbox("Enable Export Options", value=True)
    
    # Validate button - enable if there's content
    if st.button("Validate & Analyze", type="primary", disabled=(not edi_content or not edi_content.strip())):
        validate_edi_content(edi_content, {
            'enable_ai_analysis': enable_ai_analysis,
            'strict_tr3': strict_tr3,
            'show_details': show_details,
            'export_results': export_results
        })


def validate_edi_content(content, options):
    """Enhanced EDI content validation with all features."""
    
    with st.spinner("Performing comprehensive validation..."):
        try:
            if IS_STREAMLIT_CLOUD and HAS_LOCAL_PROCESSING:
                # Use embedded validation
                result = validate_with_embedded_service(content, options)
            else:
                # Use API
                payload = {
                    "content": content,
                    "filename": "validation_content.edi", 
                    "enable_ai_analysis": options.get('enable_ai_analysis', True)
                }
                
                response = requests.post(f"{API_BASE_URL}/validate", json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                else:
                    st.error(f"Validation failed: {response.text}")
                    return
            
            # Display results
            display_enhanced_validation_results(result, options)
            
        except Exception as e:
            st.error(f"Validation error: {str(e)}")


def validate_with_embedded_service(content, options):
    """Validate using embedded service."""
    try:
        processing_service = st.session_state.get('processing_service')
        
        if not processing_service:
            from app.services.processor import EDIProcessingService
            processing_service = EDIProcessingService()
            st.session_state['processing_service'] = processing_service
        
        # Create upload request for validation
        from app.core.models import EDIFileUpload
        upload_request = EDIFileUpload(
            filename="validation_content.edi",
            content_type="text/plain",
            validate_only=True,
            enable_ai_analysis=options.get('enable_ai_analysis', True),
            output_format="validation"
        )
        
        # Process content
        import asyncio
        
        async def validate_async():
            return await processing_service.process_content(content, upload_request)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        job = loop.run_until_complete(validate_async())
        
        # Store in session for later retrieval
        if 'jobs' not in st.session_state:
            st.session_state['jobs'] = {}
        st.session_state['jobs'][job.job_id] = job
        
        # Convert job to API-like response
        result = {
            "job_id": job.job_id,
            "filename": "validation_content.edi",
            "is_valid": job.validation_result.is_valid if job.validation_result else False,
            "tr3_compliance": job.validation_result.tr3_compliance if job.validation_result else False,
            "segments_validated": job.validation_result.segments_validated if job.validation_result else 0,
            "validation_time": job.validation_result.validation_time if job.validation_result else 0,
            "issues": [],
            "suggested_improvements": job.validation_result.suggested_improvements if job.validation_result else []
        }
        
        # Add issues
        if job.validation_result and job.validation_result.issues:
            for issue in job.validation_result.issues:
                result["issues"].append({
                    "level": str(issue.level) if hasattr(issue, 'level') else 'unknown',
                    "code": issue.code if hasattr(issue, 'code') else 'UNKNOWN',
                    "message": issue.message if hasattr(issue, 'message') else str(issue),
                    "segment": issue.segment if hasattr(issue, 'segment') else None,
                    "line_number": issue.line_number if hasattr(issue, 'line_number') else None,
                    "suggested_fix": issue.suggested_fix if hasattr(issue, 'suggested_fix') else None
                })
        
        # Add AI analysis if available
        if job.ai_analysis:
            result["ai_analysis"] = {
                "confidence_score": job.ai_analysis.confidence_score,
                "risk_assessment": job.ai_analysis.risk_assessment,
                "anomalies_detected": job.ai_analysis.anomalies_detected,
                "suggested_fixes": job.ai_analysis.suggested_fixes,
                "pattern_analysis": job.ai_analysis.pattern_analysis
            }
        
        return result
        
    except Exception as e:
        st.error(f"Embedded validation failed: {str(e)}")
        return None


def display_enhanced_validation_results(result, options):
    """Display enhanced validation results with all features."""
    
    if not result:
        st.error("No validation results to display")
        return
    
    # Main validation status
    is_valid = result.get("is_valid", False)
    if is_valid:
        st.success("VALIDATION PASSED - Document is valid and compliant")
    else:
        st.error("VALIDATION FAILED - Document has issues requiring attention")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Document Status", "VALID" if is_valid else "INVALID")
    with col2:
        tr3_compliance = result.get("tr3_compliance", False)
        st.metric("TR3 Compliance", "PASS" if tr3_compliance else "FAIL")
    with col3:
        segments = result.get("segments_validated", 0)
        st.metric("Segments Validated", segments)
    with col4:
        time_taken = result.get("validation_time", 0)
        st.metric("Validation Time", f"{time_taken:.3f}s")
    
    # Validation issues
    issues = result.get("issues", [])
    if issues:
        st.subheader(f"Validation Issues ({len(issues)})")
        
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            level_filter = st.selectbox("Filter by Level", ["All"] + list(set([issue.get("level", "unknown") for issue in issues])))
        with col2:
            show_fixes = st.checkbox("Show Suggested Fixes", value=True)
        
        # Display filtered issues
        filtered_issues = issues if level_filter == "All" else [issue for issue in issues if issue.get("level") == level_filter]
        
        for i, issue in enumerate(filtered_issues, 1):
            level = issue.get("level", "unknown").upper()
            message = issue.get("message", "Unknown issue")
            
            if level == "CRITICAL":
                st.error(f"{i}. **CRITICAL:** {message}")
            elif level == "ERROR":
                st.error(f"{i}. **ERROR:** {message}")
            elif level == "WARNING":
                st.warning(f"{i}. **WARNING:** {message}")
            else:
                st.info(f"{i}. **{level}:** {message}")
            
            # Show additional details
            if issue.get("segment"):
                st.caption(f"Segment: {issue['segment']}")
            if issue.get("line_number"):
                st.caption(f"Line: {issue['line_number']}")
            if show_fixes and issue.get("suggested_fix"):
                st.caption(f"Suggested Fix: {issue['suggested_fix']}")
    
    # AI Analysis (if available)
    ai_analysis = result.get("ai_analysis")
    if ai_analysis and options.get('show_details', True):
        st.subheader("AI Analysis")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            confidence = ai_analysis.get("confidence_score", 0)
            st.metric("Confidence Score", f"{confidence:.2f}")
        with col2:
            risk = ai_analysis.get("risk_assessment", "unknown").upper()
            st.metric("Risk Assessment", risk)
        with col3:
            anomalies = ai_analysis.get("anomalies_detected", [])
            st.metric("Anomalies Found", len(anomalies))
        
        if anomalies:
            st.write("**Detected Anomalies:**")
            for anomaly in anomalies:
                st.warning(anomaly)
        
        suggestions = ai_analysis.get("suggested_fixes", [])
        if suggestions:
            st.write("**AI Recommendations:**")
            for suggestion in suggestions:
                st.info(suggestion)
    
    # Export options
    if options.get('export_results', True):
        st.subheader("Export Results")
        
        col1, col2 = st.columns(2)
        with col1:
            # JSON export
            json_data = json.dumps(result, indent=2, default=str)
            st.download_button(
                "Download JSON Report",
                json_data,
                "validation_report.json",
                "application/json"
            )
        
        with col2:
            # Text report
            text_report = f"""EDI VALIDATION REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
- Status: {'VALID' if is_valid else 'INVALID'}
- TR3 Compliant: {'YES' if result.get('tr3_compliance', False) else 'NO'}
- Segments: {result.get('segments_validated', 0)}
- Issues: {len(issues)}

DETAILS:
{chr(10).join([f"- [{issue.get('level', 'unknown').upper()}] {issue.get('message', 'Unknown')}" for issue in issues])}
"""
            
            st.download_button(
                "Download Text Report", 
                text_report,
                "validation_report.txt",
                "text/plain"
            )


def display_validation_results(result):
    """Display validation results in a clean, professional format.""" 
    
    if not result:
        st.error("No validation results available")
        return
    
    # Main status
    is_valid = result.get("is_valid", False)
    if is_valid:
        st.success("Document validation completed successfully")
    else:
        st.error("Document validation found issues")
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Status", "VALID" if is_valid else "INVALID")
    with col2:
        tr3_compliant = result.get("tr3_compliance", False)
        st.metric("TR3 Compliance", "PASS" if tr3_compliant else "FAIL")
    with col3:
        segments = result.get("segments_validated", 0)
        st.metric("Segments Validated", segments)
    
    # Issues
    issues = result.get("issues", [])
    if issues:
        st.subheader(f"Issues Found ({len(issues)})")
        for issue in issues:
            level = issue.get("level", "info").upper()
            message = issue.get("message", "Unknown issue")
            
            if level in ["CRITICAL", "ERROR"]:
                st.error(f"**{level}:** {message}")
            elif level == "WARNING":
                st.warning(f"**{level}:** {message}")
            else:
                st.info(f"**{level}:** {message}")
    else:
        st.success("No validation issues found")
    
    # Suggestions
    suggestions = result.get("suggested_improvements", [])
    if suggestions:
        st.subheader("Recommendations")
        for suggestion in suggestions:
            st.info(suggestion)


def show_dashboard_page():
    """Display system dashboard with metrics and monitoring."""
    
    st.header("Dashboard")
    st.markdown("Real-time system metrics and processing statistics")
    
    try:
        # Get fresh statistics
        stats = get_statistics()
        
        # Key Metrics Row
        st.subheader("System Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_files = stats.get("total_files_processed", 0)
            st.metric("Total Files Processed", f"{total_files:,}")
        
        with col2:
            successful = stats.get("successful_conversions", 0)
            st.metric("Successful Conversions", f"{successful:,}")
        
        with col3:
            failed = stats.get("failed_conversions", 0)
            st.metric("Failed Conversions", f"{failed:,}")
        
        with col4:
            if total_files > 0:
                success_rate = (successful / total_files) * 100
                st.metric("Success Rate", f"{success_rate:.1f}%")
            else:
                st.metric("Success Rate", "0.0%")
        
        # Performance Metrics
        st.subheader("Performance Metrics")
        col1, col2 = st.columns(2)
        
        with col1:
            avg_time = stats.get("average_processing_time", 0)
            st.metric("Average Processing Time", f"{avg_time:.2f}s")
        
        with col2:
            last_updated = stats.get("last_updated")
            if last_updated:
                if isinstance(last_updated, str):
                    try:
                        last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    except:
                        last_updated = "Unknown"
                else:
                    last_updated = last_updated.strftime("%Y-%m-%d %H:%M:%S")
            else:
                last_updated = "Never"
            st.metric("Last Updated", last_updated)
        
        # Charts and Graphs
        st.subheader("Processing Analytics")
        
        # Success/Failure Chart
        if total_files > 0:
            chart_data = {
                "Status": ["Successful", "Failed"],
                "Count": [successful, failed]
            }
            
            import pandas as pd
            df = pd.DataFrame(chart_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.bar_chart(df.set_index("Status"))
            
            with col2:
                # Create pie chart data
                if successful > 0 or failed > 0:
                    sizes = [successful, failed]
                    labels = ['Successful', 'Failed']
                    
                    # Use plotly for pie chart
                    try:
                        import plotly.express as px
                        fig = px.pie(values=sizes, names=labels, title="Processing Results")
                        st.plotly_chart(fig, use_container_width=True)
                    except ImportError:
                        # Fallback if plotly not available
                        st.write("**Processing Results:**")
                        st.write(f"- Successful: {successful}")
                        st.write(f"- Failed: {failed}")
        else:
            st.info("No processing data available yet. Upload some files to see analytics.")
        
        # Common Errors
        common_errors = stats.get("most_common_errors", [])
        if common_errors:
            st.subheader("Most Common Issues")
            for i, error in enumerate(common_errors[:5], 1):
                st.write(f"{i}. {error}")
        else:
            st.info("No common errors recorded")
        
        # Recent Activity
        st.subheader("Recent Activity")
        recent_jobs = get_recent_jobs(limit=10)
        
        if recent_jobs:
            # Create a simple table of recent jobs
            job_data = []
            for job in recent_jobs:
                if isinstance(job, dict):
                    job_data.append({
                        "Job ID": job.get("job_id", "Unknown")[:8] + "...",
                        "Filename": job.get("filename", "Unknown"),
                        "Status": job.get("status", "Unknown").upper(),
                        "Time": job.get("created_at", "Unknown")
                    })
                else:
                    job_data.append({
                        "Job ID": getattr(job, 'job_id', 'Unknown')[:8] + "...",
                        "Filename": getattr(job, 'filename', 'Unknown'),
                        "Status": str(getattr(job, 'status', 'Unknown')).upper(),
                        "Time": str(getattr(job, 'created_at', 'Unknown'))
                    })
            
            if job_data:
                import pandas as pd
                df = pd.DataFrame(job_data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No recent job data available")
        else:
            st.info("No recent activity to display")
        
        # System Health
        st.subheader("System Health")
        health_col1, health_col2 = st.columns(2)
        
        with health_col1:
            # API Health Check
            try:
                health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
                if health_response.status_code == 200:
                    st.success("API Server: Online")
                else:
                    st.error("API Server: Issues detected")
            except:
                st.error("API Server: Offline")
        
        with health_col2:
            # Processing Service Health
            if IS_STREAMLIT_CLOUD and HAS_LOCAL_PROCESSING:
                st.success("Processing Service: Embedded")
            else:
                st.info("Processing Service: External API")
        
        # Auto-refresh option
        st.subheader("Auto-Refresh")
        auto_refresh = st.checkbox("Auto-refresh dashboard every 30 seconds")
        
        if auto_refresh:
            import time
            time.sleep(1)  # Small delay
            st.rerun()
    
    except Exception as e:
        st.error(f"Dashboard error: {str(e)}")
        st.info("Please check your connection and try again.")


def show_job_history_page():
    """Show job history and management."""
    
    st.header("Job History")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "completed", "failed", "processing", "pending"]
        )
    
    with col2:
        limit = st.number_input("Number of Jobs", min_value=10, max_value=100, value=20)
    
    with col3:
        if st.button("Refresh"):
            st.experimental_rerun()
    
    # Get jobs
    jobs = get_recent_jobs(limit, status_filter if status_filter != "All" else None)
    
    if jobs:
        # Jobs table
        jobs_df = pd.DataFrame(jobs)
        
        # Select columns to display
        display_columns = ['filename', 'status', 'created_at', 'processing_time', 'file_size']
        available_columns = [col for col in display_columns if col in jobs_df.columns]
        
        # Format the data
        if 'created_at' in jobs_df.columns:
            jobs_df['created_at'] = pd.to_datetime(jobs_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        if 'processing_time' in jobs_df.columns:
            jobs_df['processing_time'] = jobs_df['processing_time'].apply(
                lambda x: f"{x:.2f}s" if pd.notna(x) else "N/A"
            )
        
        if 'file_size' in jobs_df.columns:
            jobs_df['file_size'] = jobs_df['file_size'].apply(
                lambda x: f"{x:,} bytes" if pd.notna(x) else "N/A"
            )
        
        # Display table
        st.dataframe(
            jobs_df[available_columns],
            use_container_width=True
        )
        
        # Job details
        if jobs:
            st.subheader("Job Details")
            selected_job_id = st.selectbox(
                "Select Job to View Details",
                options=[job["job_id"] for job in jobs],
                format_func=lambda x: f"{x[:8]}... - {next(job['filename'] for job in jobs if job['job_id'] == x)}"
            )
            
            if selected_job_id:
                job_details = get_job_details(selected_job_id)
                if job_details:
                    st.json(job_details)
                    
                    # Download options
                    st.subheader("Download Results")
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        try:
                            response = requests.get(f"{API_BASE_URL}/jobs/{selected_job_id}/export/json")
                            if response.status_code == 200:
                                st.download_button(
                                    "JSON",
                                    response.text,
                                    f"result_{selected_job_id}.json",
                                    "application/json",
                                    key=f"history_json_{selected_job_id}"
                                )
                        except Exception as e:
                            st.text("JSON not available")
                    
                    with col2:
                        try:
                            response = requests.get(f"{API_BASE_URL}/jobs/{selected_job_id}/export/xml")
                            if response.status_code == 200:
                                st.download_button(
                                    "XML",
                                    response.text,
                                    f"result_{selected_job_id}.xml",
                                    "application/xml",
                                    key=f"history_xml_{selected_job_id}"
                                )
                        except Exception as e:
                            st.text("XML not available")
                    
                    with col3:
                        try:
                            response = requests.get(f"{API_BASE_URL}/jobs/{selected_job_id}/export/edi")
                            if response.status_code == 200:
                                st.download_button(
                                    "EDI",
                                    response.text,
                                    f"result_{selected_job_id}.edi",
                                    "text/plain",
                                    key=f"history_edi_{selected_job_id}"
                                )
                        except Exception as e:
                            st.text("EDI not available")
                    
                    with col4:
                        try:
                            response = requests.get(f"{API_BASE_URL}/jobs/{selected_job_id}/export/validation")
                            if response.status_code == 200:
                                st.download_button(
                                    "Report",
                                    response.text,
                                    f"validation_report_{selected_job_id}.json",
                                    "application/json",
                                    key=f"history_report_{selected_job_id}"
                                )
                        except Exception as e:
                            st.text("Report not available")
    else:
        st.info("No jobs found. Upload some files to see job history.")


def show_settings_page():
    """Show settings and configuration."""
    
    st.header("Settings")
    
    # API Configuration
    st.subheader("API Configuration")
    
    current_url = st.text_input("API Base URL", value=API_BASE_URL)
    
    if st.button("Test Connection"):
        test_api_connection(current_url)
    
    # Processing Settings
    st.subheader("Processing Settings")
    
    # These would typically be saved to session state or config
    default_ai_analysis = st.checkbox("Enable AI Analysis by Default", value=True)
    default_output_format = st.selectbox("Default Output Format", ["fhir", "json", "xml"])
    max_file_size = st.number_input("Max File Size (MB)", min_value=1, max_value=100, value=50)
    
    # System Information
    st.subheader("System Information")
    
    health = check_api_health()
    if health["healthy"]:
        health_data = health["data"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**API Status:** ✅ Healthy")
            st.write(f"**Version:** {health_data.get('version', 'Unknown')}")
            st.write(f"**Timestamp:** {health_data.get('timestamp', 'Unknown')}")
        
        with col2:
            components = health_data.get("components", {})
            st.write("**Components:**")
            for component, status in components.items():
                icon = "✅" if status == "healthy" else "❌" if status == "unhealthy" else "⚠️"
                st.write(f"{icon} {component.title()}: {status}")
    
    # Cache Management
    st.subheader("Cache Management")
    
    if st.button("Clear Cache"):
        st.cache_data.clear()
        st.success("Cache cleared!")
    
    # Cleanup
    if st.button("Cleanup Old Jobs"):
        cleanup_old_jobs()


def test_api_connection(url):
    """Test API connection."""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        if response.status_code == 200:
            st.success("✅ Connection successful!")
        else:
            st.error(f"❌ Connection failed: HTTP {response.status_code}")
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}")


@st.cache_data(ttl=30)  # Reduced TTL from 60 to 30 seconds for faster updates
def get_statistics():
    """Get statistics from API or session state (cached)."""
    try:
        # Try API first
        response = requests.get(f"{API_BASE_URL}/stats")
        if response.status_code == 200:
            stats = response.json()
            # Debug: ensure success rate is calculated correctly
            total = stats.get("total_files_processed", 0)
            successful = stats.get("successful_conversions", 0)
            if total > 0 and successful > 0:
                # Recalculate success rate to ensure it's correct
                calculated_rate = (successful / total) * 100
                stats["success_rate"] = calculated_rate
            return stats
    except Exception:
        pass
    
    # Fallback to session state for embedded mode
    if 'jobs' in st.session_state:
        jobs = st.session_state['jobs']
        total_files = len(jobs)
        
        # Count truly successful jobs (completed AND valid)
        successful = 0
        failed = 0
        
        for job in jobs.values():
            job_status = getattr(job, 'status', 'unknown')
            
            if job_status == 'completed':
                # Check if validation was actually successful
                validation_result = getattr(job, 'validation_result', None)
                if validation_result:
                    # Handle both dict and object validation results
                    if hasattr(validation_result, 'is_valid'):
                        is_valid = validation_result.is_valid
                    elif isinstance(validation_result, dict):
                        is_valid = validation_result.get('is_valid', False)
                    else:
                        is_valid = getattr(validation_result, 'is_valid', False)
                    
                    if is_valid:
                        successful += 1
                    else:
                        failed += 1  # Completed but invalid = failed
                else:
                    # No validation result = failed
                    failed += 1
            else:
                failed += 1
        
        success_rate = (successful / total_files * 100) if total_files > 0 else 0
        
        # Calculate average processing time
        processing_times = []
        for job in jobs.values():
            if hasattr(job, 'processing_time') and job.processing_time:
                processing_times.append(job.processing_time)
        
        avg_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Collect common errors
        common_errors = []
        for job in jobs.values():
            error_msg = getattr(job, 'error_message', None)
            if error_msg:
                # Extract key error types
                if 'pyx12' in error_msg.lower():
                    common_errors.append('pyx12 parsing errors')
                elif 'fhir' in error_msg.lower():
                    common_errors.append('FHIR mapping errors')
                elif 'validation' in error_msg.lower():
                    common_errors.append('Validation errors')
                else:
                    common_errors.append('Processing errors')
        
        # Get most common errors (top 3)
        from collections import Counter
        error_counts = Counter(common_errors)
        most_common = [error for error, count in error_counts.most_common(3)]
        
        return {
            "total_files_processed": total_files,
            "successful_conversions": successful,
            "failed_conversions": failed,
            "success_rate": success_rate,
            "average_processing_time": avg_time,
            "most_common_errors": most_common,
            "last_updated": datetime.now().isoformat()
        }
    
    return None


@st.cache_data(ttl=30)
def get_recent_jobs(limit=20, status=None):
    """Get recent jobs from API or session state (cached)."""
    try:
        # Try API first
        params = {"limit": limit}
        if status:
            params["status"] = status
        
        response = requests.get(f"{API_BASE_URL}/jobs", params=params)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    
    # Fallback to session state for embedded mode
    if 'jobs' in st.session_state:
        jobs = st.session_state['jobs']
        job_list = []
        
        for job_id, job in jobs.items():
            job_dict = {
                "job_id": job_id,
                "filename": getattr(job, 'filename', 'unknown'),
                "status": getattr(job, 'status', 'unknown'),
                "created_at": getattr(job, 'created_at', datetime.now()).isoformat() if hasattr(job, 'created_at') else datetime.now().isoformat(),
                "processing_time": getattr(job, 'processing_time', None),
                "file_size": getattr(job, 'file_size', None)
            }
            
            # Filter by status if specified
            if status is None or job_dict["status"] == status:
                job_list.append(job_dict)
        
        # Sort by created_at (newest first) and limit
        job_list.sort(key=lambda x: x["created_at"], reverse=True)
        return job_list[:limit]
    
    return []


def get_job_details(job_id):
    """Get job details from API."""
    try:
        response = requests.get(f"{API_BASE_URL}/jobs/{job_id}")
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


# download_result function removed - downloads now handled directly with st.download_button


def cleanup_old_jobs():
    """Cleanup old jobs."""
    try:
        response = requests.post(f"{API_BASE_URL}/admin/cleanup")
        if response.status_code == 200:
            st.success("✅ Cleanup completed!")
        else:
            st.error(f"Cleanup failed: {response.text}")
    except Exception as e:
        st.error(f"Cleanup error: {str(e)}")


def generate_sample_edi():
    """Generate a sample EDI file."""
    return """ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *230815*1430*U*00501*000000001*0*P*>~
GS*HS*SENDER*RECEIVER*20230815*1430*000000001*X*005010X217~
ST*278*000000001~
BHT*0078*01*SAMPLE123*20230815*1430~
HL*1**20*1~
NM1*41*2*SAMPLE HEALTHCARE*****46*123456789~
HL*2*1*21*1~
NM1*PR*2*SAMPLE INSURANCE*****46*987654321~
HL*3*2*22*0~
NM1*IL*1*DOE*JOHN*****MI*123456789~
DMG*D8*19850301*M~
UM*HS*99213*OFFICE VISIT~
SE*11*000000001~
GE*1*000000001~
IEA*1*000000001~"""


if __name__ == "__main__":
    main()