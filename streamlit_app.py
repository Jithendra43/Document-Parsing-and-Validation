"""Streamlit frontend for EDI X12 278 Processing Microservice."""

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

# Check if we're running on Streamlit Cloud (API won't be available)
IS_STREAMLIT_CLOUD = "streamlit.io" in os.getenv("STREAMLIT_SERVER_ADDRESS", "") or not os.getenv("API_BASE_URL")

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
</style>
""", unsafe_allow_html=True)

def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown('<h1 class="main-header">🏥 EDI X12 278 Processor</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center;"><strong>AI-powered EDI processing with FHIR mapping and validation</strong></p>', unsafe_allow_html=True)
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["🏠 Home", "📤 Upload & Process", "🔍 Validate Only", "📊 Dashboard", "📋 Job History", "⚙️ Settings"]
    )
    
    # Check API health
    health_status = check_api_health()
    if not health_status["healthy"]:
        st.error("⚠️ API service is unavailable. Please check the backend service.")
        return
    
    # Route to different pages
    if page == "🏠 Home":
        show_home_page()
    elif page == "📤 Upload & Process":
        show_upload_page()
    elif page == "🔍 Validate Only":
        show_validation_page()
    elif page == "📊 Dashboard":
        show_dashboard_page()
    elif page == "📋 Job History":
        show_job_history_page()
    elif page == "⚙️ Settings":
        show_settings_page()


def check_api_health():
    """Check if the API is healthy."""
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
        
        ### Getting Started
        1. Use **Upload & Process** to convert EDI files to FHIR
        2. Use **Validate Only** to check file compliance
        3. Monitor progress in the **Dashboard**
        4. Review results in **Job History**
        """)
        
        # Quick stats
        stats = get_statistics()
        if stats:
            st.subheader("Quick Statistics")
            col_a, col_b, col_c, col_d = st.columns(4)
            
            with col_a:
                st.metric("Total Files Processed", stats.get("total_files_processed", 0))
            with col_b:
                st.metric("Success Rate", f"{stats.get('success_rate', 0):.1f}%")
            with col_c:
                st.metric("Avg Processing Time", f"{stats.get('average_processing_time', 0):.2f}s")
            with col_d:
                st.metric("Failed Conversions", stats.get("failed_conversions", 0))
    
    with col2:
        st.subheader("System Status")
        health = check_api_health()
        
        if health["healthy"]:
            health_data = health["data"]
            st.success("✅ System Healthy")
            
            st.markdown("**Components:**")
            components = health_data.get("components", {})
            for component, status in components.items():
                icon = "✅" if status == "healthy" else "⚠️"
                st.write(f"{icon} {component.title()}: {status}")
        else:
            st.error(f"❌ System Unhealthy: {health['error']}")
        
        # API endpoints
        st.subheader("API Endpoints")
        st.markdown(f"""
        - **API Docs**: [{API_BASE_URL}/docs]({API_BASE_URL}/docs)
        - **Health Check**: [{API_BASE_URL}/health]({API_BASE_URL}/health)
        - **Statistics**: [{API_BASE_URL}/stats]({API_BASE_URL}/stats)
        """)


def show_upload_page():
    """Show the file upload and processing page."""
    
    st.header("📤 Upload & Process EDI Files")
    
    # File upload section
    uploaded_file = st.file_uploader(
        "Choose an EDI file",
        type=["edi", "txt", "x12"],
        help="Upload X12 278 EDI files for processing"
    )
    
    # Processing options
    st.subheader("Processing Options")
    col1, col2 = st.columns(2)
    
    with col1:
        validate_only = st.checkbox("Validation", value=False, 
                                  help="Only validate the file without conversion")
        enable_ai_analysis = st.checkbox("Enable AI Analysis", value=True,
                                       help="Use AI for anomaly detection and smart suggestions")
    
    with col2:
        output_format = st.selectbox(
            "Output Format",
            ["fhir", "json", "xml"],
            help="Choose the output format for conversion"
        )
    
    # Process button
    if st.button("Process File", type="primary", disabled=(uploaded_file is None)):
        if uploaded_file is not None:
            process_uploaded_file(uploaded_file, validate_only, enable_ai_analysis, output_format)
    
    # Sample file section
    st.subheader("Don't have a sample file?")
    if st.button("Generate Sample EDI"):
        sample_content = generate_sample_edi()
        st.code(sample_content, language="text")
        st.download_button(
            "Download Sample",
            sample_content,
            "sample_278.edi",
            "text/plain"
        )


def process_uploaded_file(uploaded_file, validate_only, enable_ai_analysis, output_format):
    """Process the uploaded file."""
    
    # Show processing message
    with st.spinner("Processing file..."):
        try:
            # Read file content
            content = uploaded_file.read().decode('utf-8')
            
            # Prepare API request
            data = {
                "content": content,
                "filename": uploaded_file.name,
                "validate_only": validate_only,
                "enable_ai_analysis": enable_ai_analysis,
                "output_format": output_format
            }
            
            # Call API
            response = requests.post(f"{API_BASE_URL}/process", json=data)
            
            if response.status_code == 200:
                result = response.json()
                display_processing_results(result, uploaded_file.name)
            else:
                st.error(f"Processing failed: {response.text}")
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")


def display_processing_results(result, filename):
    """Display processing results with improved consistency."""
    
    # Get job details
    job_id = result.get("job_id")
    status = result.get("status", "unknown")
    
    if status == "completed":
        st.success(f"✅ Successfully processed {filename}")
    elif status == "failed":
        st.error(f"❌ Processing failed for {filename}")
    else:
        st.info(f"📋 Processing {status} for {filename}")
    
    # Get detailed job information
    if job_id:
        try:
            job_response = requests.get(f"{API_BASE_URL}/jobs/{job_id}")
            if job_response.status_code == 200:
                job_details = job_response.json()
                
                # Validation summary
                validation_result = job_details.get("validation_result")
                if validation_result:
                    st.subheader("Validation Summary")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        is_valid = validation_result.get("is_valid", False)
                        st.metric("Valid", "✅" if is_valid else "❌")
                    
                    with col2:
                        tr3_compliance = validation_result.get("tr3_compliance", False)
                        st.metric("TR3 Compliant", "✅" if tr3_compliance else "❌")
                    
                    with col3:
                        segments_validated = validation_result.get("segments_validated", 0)
                        st.metric("Segments Validated", segments_validated)
                    
                    with col4:
                        validation_time = validation_result.get("validation_time", 0)
                        st.metric("Validation Time", f"{validation_time:.3f}s")
                    
                    # Issues display (same format as validation page)
                    issues = validation_result.get("issues", [])
                    if issues:
                        st.subheader(f"Validation Issues ({len(issues)} total)")
                        
                        # Create DataFrame with proper error handling
                        issues_df = pd.DataFrame(issues)
                        
                        # Ensure all required columns exist
                        required_columns = ['level', 'code', 'message', 'segment', 'line_number', 'suggested_fix']
                        for col in required_columns:
                            if col not in issues_df.columns:
                                issues_df[col] = None
                        
                        # Replace None values with appropriate defaults
                        issues_df['line_number'] = issues_df['line_number'].fillna('N/A')
                        issues_df['segment'] = issues_df['segment'].fillna('N/A')
                        issues_df['suggested_fix'] = issues_df['suggested_fix'].fillna('No suggestion available')
                        
                        # Filter options
                        level_options = issues_df['level'].unique() if 'level' in issues_df.columns else []
                        level_filter = st.multiselect(
                            "Filter by Level",
                            options=level_options,
                            default=level_options,
                            key=f"filter_{job_id}"
                        )
                        
                        if level_filter:
                            filtered_issues = issues_df[issues_df['level'].isin(level_filter)]
                        else:
                            filtered_issues = issues_df
                        
                        # Display table with improved formatting
                        if not filtered_issues.empty:
                            # Create a display version with better formatting
                            display_df = filtered_issues[required_columns].copy()
                            display_df.columns = ['Level', 'Code', 'Message', 'Segment', 'Line #', 'Suggested Fix']
                            
                            st.dataframe(
                                display_df,
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.info("No issues match the selected filter criteria.")
                
                # AI Analysis display (same format as validation page)
                ai_analysis = job_details.get("ai_analysis")
                if ai_analysis:
                    st.subheader("🤖 AI Analysis")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        confidence_score = ai_analysis.get('confidence_score', 0)
                        st.metric("Confidence Score", f"{confidence_score:.2f}")
                        st.metric("Risk Assessment", ai_analysis.get('risk_assessment', 'unknown').upper())
                    
                    with col2:
                        anomalies = ai_analysis.get("anomalies_detected", [])
                        st.metric("Anomalies Found", len(anomalies))
                    
                    if anomalies:
                        st.write("**Detected Anomalies:**")
                        for i, anomaly in enumerate(anomalies, 1):
                            st.write(f"{i}. ⚠️ {anomaly}")
                    
                    suggestions = ai_analysis.get("suggested_fixes", [])
                    if suggestions:
                        st.write("**AI Suggestions:**")
                        for i, suggestion in enumerate(suggestions, 1):
                            st.write(f"{i}. 💡 {suggestion}")
                
                # Download buttons for completed jobs
                if status == "completed":
                    st.subheader("Download Results")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        try:
                            response = requests.get(f"{API_BASE_URL}/jobs/{job_id}/export/json")
                            if response.status_code == 200:
                                st.download_button(
                                    "📄 JSON",
                                    response.text,
                                    f"result_{filename}.json",
                                    "application/json",
                                    key=f"json_{job_id}"
                                )
                            else:
                                st.text("JSON not available")
                        except Exception:
                            st.text("JSON not available")
                    
                    with col2:
                        try:
                            response = requests.get(f"{API_BASE_URL}/jobs/{job_id}/export/xml")
                            if response.status_code == 200:
                                st.download_button(
                                    "📄 XML",
                                    response.text,
                                    f"result_{filename}.xml",
                                    "application/xml",
                                    key=f"xml_{job_id}"
                                )
                            else:
                                st.text("XML not available")
                        except Exception:
                            st.text("XML not available")
                    
                    with col3:
                        try:
                            response = requests.get(f"{API_BASE_URL}/jobs/{job_id}/export/edi")
                            if response.status_code == 200:
                                st.download_button(
                                    "📄 EDI",
                                    response.text,
                                    f"result_{filename}.edi",
                                    "text/plain",
                                    key=f"edi_{job_id}"
                                )
                            else:
                                st.text("EDI not available")
                        except Exception:
                            st.text("EDI not available")
                    
                    with col4:
                        try:
                            response = requests.get(f"{API_BASE_URL}/jobs/{job_id}/export/validation")
                            if response.status_code == 200:
                                st.download_button(
                                    "📋 Report",
                                    response.text,
                                    f"validation_{filename}.json",
                                    "application/json",
                                    key=f"report_{job_id}"
                                )
                            else:
                                st.text("Report not available")
                        except Exception:
                            st.text("Report not available")
                    
        except Exception as e:
            st.error(f"Error fetching job details: {str(e)}")
    
    # Show raw result for debugging if needed
    if st.checkbox("Show raw response", key=f"raw_{job_id}"):
        st.json(result)

    # Display processing info
    with st.expander("ℹ️ Processing Information", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("File Size", f"{result.get('file_size', 0):,} bytes")
            processing_time = result.get('processing_time', 0)
            st.metric("Processing Time", f"{processing_time:.2f}s")
        
        with col2:
            validation_time = result.get('validation_result', {}).get('validation_time', 0)
            st.metric("Validation Time", f"{validation_time:.2f}s")
            segments_count = len(result.get('parsed_edi', {}).get('segments', []))
            st.metric("Segments Found", segments_count)
        
        with col3:
            # Show parsing method used
            parsing_method = result.get('parsed_edi', {}).get('parsing_method', 'unknown')
            if parsing_method == 'pyx12':
                st.success("✅ pyx12 (Industry Standard)")
                st.caption("Using professional EDI library")
            elif parsing_method == 'manual_fallback':
                st.warning("⚠️ Manual Fallback")
                st.caption("pyx12 had issues, used backup parser")
            elif parsing_method == 'manual_primary':
                st.info("🔧 Manual Parser")
                st.caption("Custom parsing implementation")
            else:
                st.error("❓ Unknown Method")
                st.caption("Parsing method unclear")
            
            # AI Analysis status
            ai_analysis = result.get('ai_analysis')
            if ai_analysis:
                confidence = ai_analysis.get('confidence_score', 0)
                st.metric("AI Confidence", f"{confidence:.1%}")
            else:
                st.metric("AI Analysis", "Disabled")


def show_validation_page():
    """Show the validation-only page."""
    
    st.header("🔍 EDI Validation")
    st.markdown("Validate your EDI files without conversion")
    
    # Text area for direct input
    st.subheader("Paste EDI Content")
    edi_content = st.text_area(
        "EDI Content",
        height=200,
        placeholder="Paste your X12 278 EDI content here..."
    )
    
    # File upload option
    st.subheader("Or Upload File")
    uploaded_file = st.file_uploader(
        "Choose an EDI file for validation",
        type=["edi", "txt", "x12"]
    )
    
    if uploaded_file:
        edi_content = uploaded_file.read().decode('utf-8')
        st.text_area("File Content Preview", edi_content[:1000] + "..." if len(edi_content) > 1000 else edi_content, height=150)
    
    # Validation options
    enable_ai_analysis = st.checkbox("Enable AI Analysis", value=True)
    
    # Validate button - enable if there's content
    if st.button("Validate", type="primary", disabled=(not edi_content or not edi_content.strip())):
        validate_edi_content(edi_content, enable_ai_analysis)


def validate_edi_content(content, enable_ai_analysis):
    """Validate EDI content."""
    
    with st.spinner("Validating..."):
        try:
            data = {
                "content": content,
                "filename": "validation.edi",
                "enable_ai_analysis": enable_ai_analysis
            }
            
            response = requests.post(f"{API_BASE_URL}/validate", json=data)
            
            if response.status_code == 200:
                result = response.json()
                display_validation_results(result)
            else:
                st.error(f"Validation failed: {response.text}")
                
        except Exception as e:
            st.error(f"Error during validation: {str(e)}")


def display_validation_results(result):
    """Display validation results with improved formatting."""
    
    is_valid = result.get("is_valid", False)
    tr3_compliance = result.get("tr3_compliance", False)
    
    # Overall status
    if is_valid and tr3_compliance:
        st.success("✅ Validation passed! File is valid and TR3 compliant.")
    elif is_valid:
        st.warning("⚠️ File is structurally valid but may have TR3 compliance issues.")
    else:
        st.error("❌ Validation failed! File has structural issues.")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Valid", "✅" if is_valid else "❌")
    with col2:
        st.metric("TR3 Compliant", "✅" if tr3_compliance else "❌")
    with col3:
        segments_validated = result.get("segments_validated", 0)
        st.metric("Segments Validated", segments_validated)
    with col4:
        validation_time = result.get("validation_time", 0)
        st.metric("Validation Time", f"{validation_time:.3f}s")
    
    # Issues
    issues = result.get("issues", [])
    if issues:
        st.subheader(f"Validation Issues ({len(issues)} total)")
        
        # Create DataFrame with proper error handling
        issues_df = pd.DataFrame(issues)
        
        # Ensure all required columns exist
        required_columns = ['level', 'code', 'message', 'segment', 'line_number', 'suggested_fix']
        for col in required_columns:
            if col not in issues_df.columns:
                issues_df[col] = None
        
        # Replace None values with appropriate defaults
        issues_df['line_number'] = issues_df['line_number'].fillna('N/A')
        issues_df['segment'] = issues_df['segment'].fillna('N/A')
        issues_df['suggested_fix'] = issues_df['suggested_fix'].fillna('No suggestion available')
        
        # Filter options
        level_options = issues_df['level'].unique() if 'level' in issues_df.columns else []
        level_filter = st.multiselect(
            "Filter by Level",
            options=level_options,
            default=level_options
        )
        
        if level_filter:
            filtered_issues = issues_df[issues_df['level'].isin(level_filter)]
        else:
            filtered_issues = issues_df
        
        # Display table with improved formatting
        if not filtered_issues.empty:
            # Create a display version with better formatting
            display_df = filtered_issues[required_columns].copy()
            display_df.columns = ['Level', 'Code', 'Message', 'Segment', 'Line #', 'Suggested Fix']
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Issue level counts with proper chart
            if len(issues_df) > 0:
                level_counts = issues_df['level'].value_counts()
                
                # Create chart data
                chart_data = pd.DataFrame({
                    'Level': level_counts.index,
                    'Count': level_counts.values
                })
                
                # Fixed plotly chart
                fig = px.bar(
                    chart_data,
                    x='Level',
                    y='Count',
                    title="Issues by Severity Level",
                    color='Level',
                    color_discrete_map={
                        'critical': '#ff4444',
                        'error': '#ff8800', 
                        'warning': '#ffcc00',
                        'info': '#4488ff'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No issues match the selected filter criteria.")
    else:
        st.success("🎉 No validation issues found!")
    
    # AI Analysis
    ai_analysis = result.get("ai_analysis")
    if ai_analysis:
        st.subheader("🤖 AI Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            confidence_score = ai_analysis.get('confidence_score', 0)
            st.metric("Confidence Score", f"{confidence_score:.2f}")
            st.metric("Risk Assessment", ai_analysis.get('risk_assessment', 'unknown').upper())
        
        with col2:
            anomalies = ai_analysis.get("anomalies_detected", [])
            st.metric("Anomalies Found", len(anomalies))
        
        if anomalies:
            st.write("**Detected Anomalies:**")
            for i, anomaly in enumerate(anomalies, 1):
                st.write(f"{i}. ⚠️ {anomaly}")
        
        suggestions = ai_analysis.get("suggested_fixes", [])
        if suggestions:
            st.write("**AI Suggestions:**")
            for i, suggestion in enumerate(suggestions, 1):
                st.write(f"{i}. 💡 {suggestion}")


def show_dashboard_page():
    """Show the dashboard with analytics and monitoring."""
    
    st.header("📊 Dashboard")
    
    # Add refresh button and auto-refresh
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("Real-time analytics and monitoring")
    with col2:
        if st.button("🔄 Refresh", help="Clear cache and refresh data"):
            st.cache_data.clear()
            st.rerun()
    
    # Get statistics
    stats = get_statistics()
    
    if stats:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_files = stats.get("total_files_processed", 0)
            st.metric(
                "Total Files",
                total_files,
                delta=None
            )
        
        with col2:
            success_rate = stats.get("success_rate", 0)
            # Show success rate with better formatting
            if success_rate > 0:
                st.metric(
                    "Success Rate",
                    f"{success_rate:.1f}%",
                    delta=f"+{success_rate:.1f}%" if success_rate > 85 else None,
                    delta_color="normal"
                )
            else:
                st.metric(
                    "Success Rate", 
                    "0.0%",
                    help="Process some files to see success rate"
                )
        
        with col3:
            successful = stats.get("successful_conversions", 0)
            st.metric(
                "Successful",
                successful,
                delta=f"+{successful}" if successful > 0 else None
            )
        
        with col4:
            failed = stats.get("failed_conversions", 0)
            st.metric(
                "Failed",
                failed,
                delta=f"+{failed}" if failed > 0 else None,
                delta_color="inverse"
            )
        
        # Additional metrics
        if total_files > 0:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                avg_time = stats.get("average_processing_time", 0)
                st.metric("Avg Processing Time", f"{avg_time:.2f}s")
            
            with col2:
                # Calculate completion rate
                completion_rate = ((successful + failed) / total_files * 100) if total_files > 0 else 0
                st.metric("Completion Rate", f"{completion_rate:.1f}%")
            
            with col3:
                last_updated = stats.get("last_updated", "Unknown")
                if last_updated != "Unknown":
                    try:
                        from datetime import datetime
                        updated_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                        st.metric("Last Updated", updated_time.strftime("%H:%M:%S"))
                    except:
                        st.metric("Last Updated", "Just now")
                else:
                    st.metric("Last Updated", "Unknown")
        
        # Charts
        st.subheader("Processing Analytics")
        
        # Get recent jobs for charts
        jobs = get_recent_jobs(50)
        
        if jobs:
            # Status distribution
            col1, col2 = st.columns(2)
            
            with col1:
                status_counts = pd.Series([job["status"] for job in jobs]).value_counts()
                fig = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="Job Status Distribution",
                    color_discrete_map={
                        'completed': '#28a745',
                        'failed': '#dc3545', 
                        'processing': '#ffc107',
                        'pending': '#6c757d'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Processing time over time (if available)
                jobs_df = pd.DataFrame(jobs)
                if 'processing_time' in jobs_df.columns and not jobs_df['processing_time'].isna().all():
                    # Filter out None values
                    valid_times = jobs_df[jobs_df['processing_time'].notna()].copy()
                    if not valid_times.empty:
                        valid_times['created_at'] = pd.to_datetime(valid_times['created_at'])
                        fig = px.line(
                            valid_times.sort_values('created_at'),
                            x='created_at',
                            y='processing_time',
                            title="Processing Time Trend",
                            labels={'processing_time': 'Time (seconds)', 'created_at': 'Time'}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No processing time data available yet")
                else:
                    st.info("No processing time data available yet")
        
        # Common errors
        common_errors = stats.get("most_common_errors", [])
        if common_errors:
            st.subheader("Most Common Errors")
            for i, error in enumerate(common_errors[:5]):
                st.write(f"{i+1}. {error}")
        else:
            st.success("🎉 No common errors found!")
    
    else:
        st.info("No statistics available yet. Process some files to see analytics.")
        st.markdown("""
        **To get started:**
        1. Go to the Upload & Process page
        2. Upload an EDI file or use the sample generator
        3. Process the file
        4. Return here to see analytics
        """)
        
        # Add a test button for debugging
        if st.button("🔍 Test API Connection"):
            try:
                response = requests.get(f"{API_BASE_URL}/health")
                if response.status_code == 200:
                    st.success("✅ API is running correctly")
                    # Also test stats endpoint
                    stats_response = requests.get(f"{API_BASE_URL}/stats")
                    if stats_response.status_code == 200:
                        st.info(f"📊 Stats endpoint working: {stats_response.json()}")
                    else:
                        st.warning(f"⚠️ Stats endpoint issue: {stats_response.status_code}")
                else:
                    st.error(f"❌ API health check failed: {response.status_code}")
            except Exception as e:
                st.error(f"❌ Cannot connect to API: {str(e)}")


def show_job_history_page():
    """Show job history and management."""
    
    st.header("📋 Job History")
    
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
    
    st.header("⚙️ Settings")
    
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
    """Get statistics from API (cached)."""
    try:
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
    return None


@st.cache_data(ttl=30)
def get_recent_jobs(limit=20, status=None):
    """Get recent jobs from API (cached)."""
    try:
        params = {"limit": limit}
        if status:
            params["status"] = status
        
        response = requests.get(f"{API_BASE_URL}/jobs", params=params)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
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