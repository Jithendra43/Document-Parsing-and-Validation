"""FastAPI application for EDI X12 278 processing microservice."""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import shutil
from pathlib import Path
from typing import List, Optional
import uuid

from ..config import settings, ensure_directories
from ..core.models import (
    EDIFileUpload, EDIProcessingResponse, ProcessingJob, 
    HealthCheck, EDIStatistics, ProcessingStatus
)
from pydantic import BaseModel
from ..services.processor import EDIProcessingService, EDIProcessingError
from ..core.logger import get_logger

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered EDI X12 278 processing with FHIR mapping",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize the processing service
processor = EDIProcessingService()

# Ensure required directories exist
ensure_directories()

# Mount static files if they exist
static_path = Path("static")
if static_path.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info("Starting EDI X12 278 Processing Microservice")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"AI analysis: {'enabled' if settings.groq_api_key else 'disabled'}")
    
    # Start background cleanup task
    asyncio.create_task(periodic_cleanup())


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("Shutting down EDI X12 278 Processing Microservice")


async def periodic_cleanup():
    """Periodic cleanup of old jobs."""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            await processor.cleanup_old_jobs()
        except Exception as e:
            logger.error(f"Cleanup task failed: {str(e)}")


# Health Check Endpoints
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    components = {
        "parser": "healthy",
        "validator": "healthy",
        "fhir_mapper": "healthy",
        "ai_analyzer": "healthy" if processor.ai_analyzer else "disabled"
    }
    
    return HealthCheck(
        status="healthy",
        version=settings.app_version,
        components=components
    )


@app.get("/stats", response_model=EDIStatistics)
async def get_statistics():
    """Get processing statistics."""
    stats = processor.get_statistics()
    return EDIStatistics(**stats)


# File Upload Endpoints
@app.post("/upload", response_model=EDIProcessingResponse)
async def upload_edi_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    validate_only: bool = False,
    enable_ai_analysis: bool = True,
    output_format: str = "fhir"
):
    """
    Upload and process an EDI file.
    
    Args:
        file: EDI file to process
        validate_only: Only validate, don't convert
        enable_ai_analysis: Enable AI-powered analysis
        output_format: Output format (fhir, xml, json)
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        if not file.filename.endswith(('.edi', '.txt', '.x12')):
            raise HTTPException(
                status_code=400, 
                detail="Invalid file type. Only .edi, .txt, and .x12 files are supported"
            )
        
        # Check file size
        if file.size and file.size > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.max_file_size} bytes"
            )
        
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_path = Path(settings.upload_dir) / f"{file_id}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Create upload request
        upload_request = EDIFileUpload(
            filename=file.filename,
            content_type=file.content_type or "text/plain",
            validate_only=validate_only,
            enable_ai_analysis=enable_ai_analysis,
            output_format=output_format
        )
        
        # Start processing in background
        background_tasks.add_task(
            process_file_background,
            str(file_path),
            upload_request
        )
        
        # Create initial response
        job_id = str(uuid.uuid4())
        return EDIProcessingResponse(
            job_id=job_id,
            status=ProcessingStatus.PENDING,
            message="File uploaded successfully. Processing started.",
            validation_summary={"status": "pending"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


class ProcessEDIRequest(BaseModel):
    """Request model for processing EDI content."""
    content: str
    filename: str = "content.edi"
    validate_only: bool = False
    enable_ai_analysis: bool = True
    output_format: str = "fhir"


@app.post("/process", response_model=EDIProcessingResponse)
async def process_edi_content(request: ProcessEDIRequest):
    """
    Process EDI content directly via API.
    
    Args:
        request: ProcessEDIRequest containing content and processing options
    """
    try:
        # Validate content
        if not request.content.strip():
            raise HTTPException(status_code=400, detail="No content provided")
        
        if len(request.content) > settings.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"Content too large. Maximum size: {settings.max_file_size} bytes"
            )
        
        # Create upload request
        upload_request = EDIFileUpload(
            filename=request.filename,
            content_type="text/plain",
            validate_only=request.validate_only,
            enable_ai_analysis=request.enable_ai_analysis,
            output_format=request.output_format
        )
        
        # Process content
        job = await processor.process_content(request.content, upload_request)
        
        # Create response
        response = EDIProcessingResponse(
            job_id=job.job_id,
            status=job.status,
            message="Processing completed" if job.status == ProcessingStatus.COMPLETED 
                   else f"Processing failed: {job.error_message}",
        )
        
        # Add validation summary
        if job.validation_result:
            response.validation_summary = {
                "is_valid": job.validation_result.is_valid,
                "tr3_compliance": job.validation_result.tr3_compliance,
                "issues_count": len(job.validation_result.issues),
                "processing_time": job.processing_time
            }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


async def process_file_background(file_path: str, upload_request: EDIFileUpload):
    """Background task for file processing."""
    try:
        job = await processor.process_file(file_path, upload_request)
        logger.info(f"Background processing completed for job {job.job_id}")
    except Exception as e:
        logger.error(f"Background processing failed: {str(e)}")
    finally:
        # Clean up uploaded file
        Path(file_path).unlink(missing_ok=True)


# Job Management Endpoints
@app.get("/jobs/{job_id}", response_model=ProcessingJob)
async def get_job_status(job_id: str):
    """Get job status and results."""
    job = processor.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/jobs")
async def list_jobs(limit: int = 50, status: Optional[str] = None):
    """List recent jobs with optional status filter."""
    jobs = processor.get_all_jobs()
    
    # Filter by status if provided
    if status:
        try:
            status_enum = ProcessingStatus(status)
            jobs = {k: v for k, v in jobs.items() if v.status == status_enum}
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    # Sort by creation time (newest first) and limit
    sorted_jobs = sorted(jobs.values(), key=lambda x: x.created_at, reverse=True)
    return sorted_jobs[:limit]


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its results."""
    if job_id not in processor.jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    del processor.jobs[job_id]
    return {"message": "Job deleted successfully"}


# Export Endpoints
@app.get("/jobs/{job_id}/export/{format}")
async def export_results(job_id: str, format: str):
    """
    Export job results in specified format.
    
    Args:
        job_id: Job identifier
        format: Export format (json, xml, edi, validation)
    """
    if format not in ["json", "xml", "edi", "validation"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid format. Supported: json, xml, edi, validation"
        )
    
    try:
        content = await processor.export_results(job_id, format)
        if content is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Determine content type and filename
        content_type_map = {
            "json": "application/json",
            "xml": "application/xml",
            "edi": "text/plain",
            "validation": "application/json"
        }
        
        file_extension_map = {
            "json": "json",
            "xml": "xml", 
            "edi": "edi",
            "validation": "json"
        }
        
        content_type = content_type_map.get(format, "text/plain")
        extension = file_extension_map.get(format, "txt")
        filename = f"export_{job_id}.{extension}"
        
        # Return content directly for API
        return PlainTextResponse(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except EDIProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Export failed")


@app.get("/jobs/{job_id}/download/{format}")
async def download_results(job_id: str, format: str):
    """
    Download job results as a file.
    
    Args:
        job_id: Job identifier
        format: Export format (json, xml, edi, validation)
    """
    try:
        content = await processor.export_results(job_id, format)
        if content is None:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Create temporary file
        file_extension_map = {
            "json": "json",
            "xml": "xml",
            "edi": "edi", 
            "validation": "json"
        }
        
        extension = file_extension_map.get(format, "txt")
        temp_file = Path(settings.temp_dir) / f"download_{job_id}.{extension}"
        
        temp_file.write_text(content, encoding='utf-8')
        
        return FileResponse(
            path=str(temp_file),
            filename=f"edi_export_{job_id}.{extension}",
            media_type="application/octet-stream"
        )
        
    except EDIProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Download failed")


# Validation Endpoints
class ValidateEDIRequest(BaseModel):
    """Request model for validating EDI content."""
    content: str
    filename: str = "content.edi"
    enable_ai_analysis: bool = True


@app.post("/validate")
async def validate_edi_content(request: ValidateEDIRequest):
    """
    Validate EDI content without conversion.
    
    Args:
        request: ValidateEDIRequest containing content and validation options
    """
    try:
        upload_request = EDIFileUpload(
            filename=request.filename,
            content_type="text/plain",
            validate_only=True,
            enable_ai_analysis=request.enable_ai_analysis,
            output_format="validation"
        )
        
        job = await processor.process_content(request.content, upload_request)
        
        if not job.validation_result:
            raise HTTPException(status_code=500, detail="Validation failed")
        
        # Return detailed validation results
        result = {
            "job_id": job.job_id,
            "filename": request.filename,
            "is_valid": job.validation_result.is_valid,
            "tr3_compliance": job.validation_result.tr3_compliance,
            "segments_validated": job.validation_result.segments_validated,
            "validation_time": job.validation_result.validation_time,
            "issues": [
                {
                    "level": issue.level,
                    "code": issue.code,
                    "message": issue.message,
                    "segment": issue.segment,
                    "line_number": issue.line_number,
                    "suggested_fix": issue.suggested_fix
                }
                for issue in job.validation_result.issues
            ],
            "suggested_improvements": job.validation_result.suggested_improvements
        }
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


# FHIR Endpoints
class ConvertToFHIRRequest(BaseModel):
    """Request model for converting EDI content to FHIR."""
    content: str
    filename: str = "content.edi"


@app.post("/convert/fhir")
async def convert_to_fhir(request: ConvertToFHIRRequest):
    """
    Convert EDI content to FHIR format.
    
    Args:
        request: ConvertToFHIRRequest containing content and filename
    """
    try:
        upload_request = EDIFileUpload(
            filename=request.filename,
            content_type="text/plain",
            validate_only=False,
            enable_ai_analysis=False,
            output_format="fhir"
        )
        
        job = await processor.process_content(request.content, upload_request)
        
        if job.status != ProcessingStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail=f"Conversion failed: {job.error_message}"
            )
        
        if not job.fhir_mapping:
            raise HTTPException(status_code=500, detail="FHIR mapping failed")
        
        # Return FHIR resources
        return {
            "job_id": job.job_id,
            "mapping_version": job.fhir_mapping.mapping_version,
            "mapped_at": job.fhir_mapping.mapped_at,
            "source_segments": job.fhir_mapping.source_segments,
            "resources": [
                {
                    "resource_type": resource.resource_type,
                    "id": resource.id,
                    "data": resource.data
                }
                for resource in job.fhir_mapping.resources
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FHIR conversion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"FHIR conversion failed: {str(e)}")


# Admin Endpoints
@app.post("/admin/cleanup")
async def cleanup_old_jobs(max_age_hours: int = 24):
    """Admin endpoint to cleanup old jobs."""
    try:
        await processor.cleanup_old_jobs(max_age_hours)
        return {"message": f"Cleanup completed for jobs older than {max_age_hours} hours"}
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Cleanup failed")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "AI-powered EDI X12 278 processing with FHIR mapping",
        "docs_url": "/docs",
        "health_check": "/health",
        "upload_endpoint": "/upload",
        "validation_endpoint": "/validate",
        "fhir_conversion": "/convert/fhir"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )