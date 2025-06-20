"""Main EDI processing service orchestrating all components."""

import uuid
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from ..config import settings
from ..core.models import (
    ProcessingJob, ProcessingStatus, EDIFileUpload, 
    ParsedEDI, ValidationResult, FHIRMapping, AIAnalysis, FHIRMappingResult, FHIRResource
)
from ..core.edi_parser import EDI278Parser, EDI278Validator, EDIParsingError
from ..core.fhir_mapper import X12To278FHIRMapper, FHIRToX12Mapper, FHIRMappingError
from ..ai.analyzer import EDIAIAnalyzer, SmartEDIValidator, AIAnalysisError
from ..core.logger import get_logger

logger = get_logger(__name__)


class EDIProcessingError(Exception):
    """Custom exception for EDI processing errors."""
    pass


class EDIProcessingService:
    """Main service for processing EDI files with AI analysis and FHIR mapping."""
    
    def __init__(self):
        """Initialize the EDI processing service."""
        self.parser = EDI278Parser()
        self.validator = EDI278Validator()
        self.ai_analyzer = EDIAIAnalyzer()
        self.fhir_mapper = X12To278FHIRMapper()
        self.jobs: Dict[str, ProcessingJob] = {}
        self.logger = get_logger(__name__)
        
        # Initialize directories
        self.upload_dir = Path(settings.upload_dir)
        self.output_dir = Path(settings.output_dir)
        self.temp_dir = Path(settings.temp_dir)
        
        # Create directories if they don't exist
        for directory in [self.upload_dir, self.output_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"📁 Directory ready: {directory}")
        
        # Initialize smart validator with AI if available
        self.smart_validator = None
        try:
            if self.ai_analyzer.is_available:
                self.smart_validator = SmartEDIValidator(self.ai_analyzer)
                logger.info("🤖 AI-enhanced validation enabled")
            else:
                logger.info("📊 Using standard validation (AI not available)")
        except Exception as e:
            logger.warning(f"Smart validator initialization warning: {str(e)}")
        
        # Initialize statistics
        self.stats = {
            "total_files_processed": 0,
            "successful_conversions": 0,
            "failed_conversions": 0,
            "average_processing_time": 0.0,
            "most_common_errors": [],
            "last_updated": datetime.utcnow()
        }
        
        logger.info("✅ EDI Processing Service initialized")
        logger.info(f"🤖 AI Analysis: {'enabled' if self.ai_analyzer.is_available else 'disabled'}")
        logger.info(f"🔄 FHIR Mapping: enabled")
        logger.info(f"✅ Validation: enabled")
    
    async def process_file(self, file_path: str, upload_request: EDIFileUpload) -> ProcessingJob:
        """
        Process an EDI file with comprehensive validation and conversion.
        
        Args:
            file_path: Path to the EDI file
            upload_request: Upload request details
            
        Returns:
            ProcessingJob: Processing job with results
        """
        job_id = str(uuid.uuid4())
        
        # Get file size
        try:
            file_size = Path(file_path).stat().st_size
        except Exception:
            file_size = 0
        
        # Create job
        job = ProcessingJob(
            job_id=job_id,
            filename=upload_request.filename,
            status=ProcessingStatus.PROCESSING,
            started_at=datetime.utcnow(),
            file_size=file_size
        )
        
        self.jobs[job_id] = job
        
        try:
            logger.info(f"[{job_id}] Starting processing for {upload_request.filename}")
            
            # Parse EDI file
            job.parsed_edi = await self._parse_edi_file(file_path)
            
            # Validate
            job.validation_result = await self._validate_edi(job.parsed_edi, upload_request)
            
            # Map to FHIR if not validation-only
            if not upload_request.validate_only:
                try:
                    job.fhir_mapping = await self._map_to_fhir(job.parsed_edi)
                    logger.info(f"[{job_id}] FHIR mapping completed successfully")
                except Exception as e:
                    logger.warning(f"[{job_id}] FHIR mapping failed: {str(e)} - continuing without FHIR mapping")
                    job.fhir_mapping = None
            
            # AI analysis if enabled and requested
            if upload_request.enable_ai_analysis and self.ai_analyzer.is_available:
                try:
                    job.ai_analysis = await self._analyze_with_ai(job.parsed_edi, job.validation_result)
                    logger.info(f"[{job_id}] AI analysis completed successfully")
                except Exception as e:
                    logger.warning(f"[{job_id}] AI analysis failed: {str(e)} - continuing without AI analysis")
                    job.ai_analysis = None
            elif upload_request.enable_ai_analysis and not self.ai_analyzer.is_available:
                logger.info(f"[{job_id}] AI analysis requested but not available")
            
            # Complete job
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.processing_time = (job.completed_at - job.started_at).total_seconds()
            
            # Update statistics
            self.stats["total_files_processed"] += 1
            self.stats["successful_conversions"] += 1
            self.stats["last_updated"] = datetime.utcnow()
            
            logger.info(f"[{job_id}] Processing completed successfully in {job.processing_time:.2f}s")
            return job
            
        except Exception as e:
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job.processing_time = (job.completed_at - job.started_at).total_seconds() if job.started_at else 0
            
            # Update statistics
            self.stats["total_files_processed"] += 1
            self.stats["failed_conversions"] += 1
            self.stats["last_updated"] = datetime.utcnow()
            
            logger.error(f"[{job_id}] Processing failed: {str(e)}")
            return job
    
    async def process_content(self, content: str, upload_request: EDIFileUpload) -> ProcessingJob:
        """
        Process EDI content from string.
        
        Args:
            content: EDI content as string
            upload_request: Upload request details
            
        Returns:
            ProcessingJob: Processing job with results
        """
        job_id = str(uuid.uuid4())
        
        # Create job
        job = ProcessingJob(
            job_id=job_id,
            filename=upload_request.filename,
            status=ProcessingStatus.PROCESSING,
            started_at=datetime.utcnow(),
            file_size=len(content.encode('utf-8'))
        )
        
        self.jobs[job_id] = job
        
        try:
            logger.info(f"[{job_id}] Starting content processing")
            
            # Parse EDI content directly
            job.parsed_edi = await self._parse_edi_content(content, upload_request.filename)
            
            # Validate
            job.validation_result = await self._validate_edi(job.parsed_edi, upload_request)
            
            # Map to FHIR if not validation-only
            if not upload_request.validate_only:
                try:
                    job.fhir_mapping = await self._map_to_fhir(job.parsed_edi)
                    logger.info(f"[{job_id}] FHIR mapping completed successfully")
                except Exception as e:
                    logger.warning(f"[{job_id}] FHIR mapping failed: {str(e)} - continuing without FHIR mapping")
                    job.fhir_mapping = None
            
            # AI analysis if enabled and available
            if upload_request.enable_ai_analysis and self.ai_analyzer.is_available:
                try:
                    job.ai_analysis = await self._analyze_with_ai(job.parsed_edi, job.validation_result)
                    logger.info(f"[{job_id}] AI analysis completed successfully")
                except Exception as e:
                    logger.warning(f"[{job_id}] AI analysis failed: {str(e)} - continuing without AI analysis")
                    job.ai_analysis = None
            elif upload_request.enable_ai_analysis and not self.ai_analyzer.is_available:
                logger.info(f"[{job_id}] AI analysis requested but not available")
            
            # Complete job
            job.status = ProcessingStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.processing_time = (job.completed_at - job.started_at).total_seconds()
            
            # Update statistics
            self.stats["total_files_processed"] += 1
            self.stats["successful_conversions"] += 1
            self.stats["last_updated"] = datetime.utcnow()
            
            logger.info(f"[{job_id}] Content processing completed successfully in {job.processing_time:.2f}s")
            return job
            
        except Exception as e:
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            job.processing_time = (job.completed_at - job.started_at).total_seconds() if job.started_at else 0
            
            # Update statistics
            self.stats["total_files_processed"] += 1
            self.stats["failed_conversions"] += 1
            self.stats["last_updated"] = datetime.utcnow()
            
            logger.error(f"[{job_id}] Content processing failed: {str(e)}")
            return job
    
    async def _parse_edi_file(self, file_path: str) -> ParsedEDI:
        """Parse EDI file."""
        try:
            # Run in thread pool for CPU-bound operation
            loop = asyncio.get_event_loop()
            parsed_edi = await loop.run_in_executor(
                None, self.parser.parse_file, file_path
            )
            return parsed_edi
        except EDIParsingError:
            raise
        except Exception as e:
            raise EDIProcessingError(f"Failed to parse EDI file: {str(e)}")
    
    async def _parse_edi_content(self, content: str, filename: str) -> ParsedEDI:
        """Parse EDI content from string."""
        try:
            # Run in thread pool for CPU-bound operation
            loop = asyncio.get_event_loop()
            parsed_edi = await loop.run_in_executor(
                None, self.parser.parse_content, content, filename
            )
            return parsed_edi
        except EDIParsingError:
            raise
        except Exception as e:
            raise EDIProcessingError(f"Failed to parse EDI content: {str(e)}")
    
    async def _validate_edi(self, parsed_edi: ParsedEDI, 
                           upload_request: EDIFileUpload) -> ValidationResult:
        """Validate parsed EDI with optional AI enhancement."""
        try:
            # Run basic validation in thread pool
            loop = asyncio.get_event_loop()
            validation_result = await loop.run_in_executor(
                None, self.validator.validate, parsed_edi
            )
            
            # Enhance with AI if available and requested
            if upload_request.enable_ai_analysis and self.smart_validator:
                try:
                    enhanced_result = await self.smart_validator.enhanced_validate(
                        parsed_edi, validation_result
                    )
                    logger.debug("AI-enhanced validation completed")
                    return enhanced_result
                except Exception as e:
                    logger.warning(f"AI-enhanced validation failed, using standard: {str(e)}")
                    return validation_result
            
            return validation_result
            
        except Exception as e:
            raise EDIProcessingError(f"Failed to validate EDI: {str(e)}")
    
    async def _analyze_with_ai(self, parsed_edi: ParsedEDI, 
                              validation_result: ValidationResult) -> Optional[AIAnalysis]:
        """
        Perform AI analysis if available.
        
        Args:
            parsed_edi: Parsed EDI structure
            validation_result: Validation results
            
        Returns:
            AIAnalysis or None: AI analysis results or None if unavailable
        """
        if not self.ai_analyzer.is_available:
            logger.info("AI analysis requested but analyzer not available")
            return None
        
        try:
            logger.info("🧠 Performing AI analysis...")
            ai_analysis = await self.ai_analyzer.analyze_edi(parsed_edi, validation_result)
            logger.info(f"✅ AI analysis completed with confidence: {ai_analysis.confidence_score:.2f}")
            return ai_analysis
        except AIAnalysisError as e:
            logger.warning(f"AI analysis failed with known error: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"AI analysis failed with unexpected error: {str(e)}")
            return None
    
    async def _map_to_fhir(self, parsed_edi: ParsedEDI) -> FHIRMapping:
        """Map EDI to FHIR resources."""
        try:
            # Run in thread pool for CPU-bound operation
            loop = asyncio.get_event_loop()
            fhir_mapping_result = await loop.run_in_executor(
                None, self.fhir_mapper.map_to_fhir, parsed_edi
            )
            
            # Convert FHIRMappingResult to FHIRMapping
            fhir_resources = []
            if fhir_mapping_result.fhir_bundle and 'entry' in fhir_mapping_result.fhir_bundle:
                for entry in fhir_mapping_result.fhir_bundle['entry']:
                    resource_data = entry.get('resource', {})
                    resource_type = resource_data.get('resourceType', 'Unknown')
                    resource_id = resource_data.get('id', '')
                    
                    fhir_resources.append(FHIRResource(
                        resource_type=resource_type,
                        id=resource_id,
                        data=resource_data
                    ))
            
            return FHIRMapping(
                resources=fhir_resources,
                mapping_version="1.0",
                mapped_at=fhir_mapping_result.generated_at,
                source_segments=[seg.segment_id for seg in parsed_edi.segments[:10]]
            )
            
        except FHIRMappingError:
            raise
        except Exception as e:
            raise EDIProcessingError(f"Failed to map to FHIR: {str(e)}")
    
    def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get job by ID."""
        return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> Dict[str, ProcessingJob]:
        """Get all jobs (for admin/monitoring)."""
        return self.jobs.copy()
    
    async def export_results(self, job_id: str, format: str = "json") -> Optional[str]:
        """
        Export job results in specified format.
        
        Args:
            job_id: Job identifier
            format: Export format (json, xml, edi, validation)
            
        Returns:
            str: Exported content or None if job not found
        """
        job = self.get_job(job_id)
        if not job:
            return None
        
        try:
            if format == "json":
                return self._export_as_json(job)
            elif format == "xml":
                return self._export_as_xml(job)
            elif format == "edi":
                return await self._export_as_edi(job)
            elif format == "validation":
                return self._export_validation_report(job)
            else:
                raise EDIProcessingError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Export failed for job {job_id}: {str(e)}")
            raise EDIProcessingError(f"Export failed: {str(e)}")
    
    def _export_as_json(self, job: ProcessingJob) -> str:
        """Export results as JSON."""
        try:
            if job.fhir_mapping and job.fhir_mapping.resources:
                # Export FHIR resources as JSON
                export_data = {
                    "resourceType": "Bundle",
                    "id": job.job_id,
                    "type": "collection",
                    "timestamp": job.fhir_mapping.mapped_at.isoformat(),
                    "entry": []
                }
                
                for resource in job.fhir_mapping.resources:
                    export_data["entry"].append({
                        "resource": resource.data
                    })
                
                import json
                return json.dumps(export_data, indent=2)
            else:
                # Export parsed EDI data as JSON
                return self._export_parsed_edi_as_json(job)
                
        except Exception as e:
            raise EDIProcessingError(f"JSON export failed: {str(e)}")
    
    def _export_parsed_edi_as_json(self, job: ProcessingJob) -> str:
        """Export parsed EDI data as JSON."""
        if not job.parsed_edi:
            raise EDIProcessingError("No parsed EDI data available")
        
        # Create a JSON representation of the parsed EDI
        export_data = {
            "job_id": job.job_id,
            "filename": job.filename,
            "processing_status": job.status,
            "file_size": job.parsed_edi.file_size,
            "parsed_at": job.parsed_edi.parsed_at.isoformat(),
            "header": {
                "transaction_type": job.parsed_edi.header.transaction_type,
                "version": job.parsed_edi.header.version,
                "sender_id": job.parsed_edi.header.sender_id,
                "receiver_id": job.parsed_edi.header.receiver_id,
                "isa_control_number": job.parsed_edi.header.isa_control_number,
                "gs_control_number": job.parsed_edi.header.gs_control_number,
                "st_control_number": job.parsed_edi.header.st_control_number,
                "interchange_date": job.parsed_edi.header.interchange_date.isoformat() if job.parsed_edi.header.interchange_date else None
            },
            "segments": [
                {
                    "segment_id": seg.segment_id,
                    "elements": seg.elements,
                    "position": seg.position,
                    "loop_id": seg.loop_id,
                    "hl_level": seg.hl_level
                }
                for seg in job.parsed_edi.segments
            ],
            "validation": self._serialize_validation_result(job.validation_result) if job.validation_result else None,
            "ai_analysis": self._serialize_ai_analysis(job.ai_analysis) if job.ai_analysis else None
        }
        
        import json
        return json.dumps(export_data, indent=2)
    
    def _serialize_validation_result(self, validation_result) -> dict:
        """Serialize validation result to JSON-compatible format."""
        if not validation_result:
            return {}
        
        result = {
            "is_valid": validation_result.is_valid,
            "tr3_compliance": validation_result.tr3_compliance,
            "segments_validated": validation_result.segments_validated,
            "validation_time": validation_result.validation_time,
            "suggested_improvements": validation_result.suggested_improvements or []
        }
        
        # Properly serialize ValidationIssue objects
        if hasattr(validation_result, 'issues') and validation_result.issues:
            result["issues"] = []
            for issue in validation_result.issues:
                try:
                    if hasattr(issue, 'model_dump'):
                        # Pydantic v2 model
                        result["issues"].append(issue.model_dump())
                    elif hasattr(issue, 'dict'):
                        # Pydantic v1 model
                        result["issues"].append(issue.dict())
                    elif isinstance(issue, dict):
                        # Already a dict
                        result["issues"].append(issue)
                    else:
                        # Convert to dict manually
                        issue_dict = {
                            "level": str(getattr(issue, 'level', 'unknown')),
                            "code": str(getattr(issue, 'code', 'UNKNOWN')),
                            "message": str(getattr(issue, 'message', str(issue))),
                            "segment": str(getattr(issue, 'segment', '')) if getattr(issue, 'segment', None) else None,
                            "element": str(getattr(issue, 'element', '')) if getattr(issue, 'element', None) else None,
                            "line_number": int(getattr(issue, 'line_number', 0)) if getattr(issue, 'line_number', None) else None,
                            "suggested_fix": str(getattr(issue, 'suggested_fix', '')) if getattr(issue, 'suggested_fix', None) else None
                        }
                        result["issues"].append(issue_dict)
                except Exception as e:
                    # Fallback for problematic objects
                    result["issues"].append({
                        "level": "error",
                        "code": "SERIALIZATION_ERROR",
                        "message": f"Failed to serialize validation issue: {str(e)}",
                        "segment": None,
                        "element": None,
                        "line_number": None,
                        "suggested_fix": None
                    })
        else:
            result["issues"] = []
        
        return result
    
    def _serialize_ai_analysis(self, ai_analysis) -> dict:
        """Serialize AI analysis to JSON-compatible format."""
        if not ai_analysis:
            return {}
        
        try:
            # Handle both Pydantic models and dict objects
            if hasattr(ai_analysis, 'model_dump'):
                # Pydantic v2 model
                return ai_analysis.model_dump()
            elif hasattr(ai_analysis, 'dict'):
                # Pydantic v1 model
                return ai_analysis.dict()
            elif isinstance(ai_analysis, dict):
                # Already a dict
                return ai_analysis
            else:
                # Convert to dict manually
                return {
                    "anomalies_detected": getattr(ai_analysis, 'anomalies_detected', []),
                    "confidence_score": getattr(ai_analysis, 'confidence_score', 0.0),
                    "suggested_fixes": getattr(ai_analysis, 'suggested_fixes', []),
                    "pattern_analysis": getattr(ai_analysis, 'pattern_analysis', {}),
                    "risk_assessment": getattr(ai_analysis, 'risk_assessment', 'unknown')
                }
        except Exception as e:
            logger.warning(f"Failed to serialize AI analysis: {str(e)}")
            return {"error": "serialization_failed", "message": str(e)}
    
    def _export_as_xml(self, job: ProcessingJob) -> str:
        """Export FHIR resources as XML."""
        if not job.fhir_mapping:
            raise EDIProcessingError("No FHIR mapping available for XML export")
        
        # Basic XML export (in production, use proper FHIR XML serialization)
        xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_content += '<Bundle xmlns="http://hl7.org/fhir">\n'
        xml_content += f'  <id value="{job.job_id}"/>\n'
        xml_content += '  <type value="collection"/>\n'
        
        for resource in job.fhir_mapping.resources:
            xml_content += f'  <entry>\n'
            xml_content += f'    <resource>\n'
            xml_content += f'      <{resource.resource_type}>\n'
            xml_content += f'        <id value="{resource.id}"/>\n'
            xml_content += f'        <!-- Resource content -->\n'
            xml_content += f'      </{resource.resource_type}>\n'
            xml_content += f'    </resource>\n'
            xml_content += f'  </entry>\n'
        
        xml_content += '</Bundle>'
        return xml_content
    
    async def _export_as_edi(self, job: ProcessingJob) -> str:
        """Export back to EDI format."""
        if not job.parsed_edi:
            raise EDIProcessingError("No parsed EDI data available")
        
        # Return the original raw content if available
        return job.parsed_edi.raw_content
    
    def _export_validation_report(self, job: ProcessingJob) -> str:
        """Export validation report."""
        if not job.validation_result:
            raise EDIProcessingError("No validation results available")
        
        report = {
            "job_id": job.job_id,
            "filename": job.filename,
            "processing_time": job.processing_time,
            "validation": self._serialize_validation_result(job.validation_result)
        }
        
        # Add AI analysis if available
        if job.ai_analysis:
            report["ai_analysis"] = self._serialize_ai_analysis(job.ai_analysis)
        
        import json
        return json.dumps(report, indent=2)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        total_jobs = len(self.jobs)
        completed_jobs = sum(1 for job in self.jobs.values() 
                           if job.status == ProcessingStatus.COMPLETED)
        failed_jobs = sum(1 for job in self.jobs.values() 
                        if job.status == ProcessingStatus.FAILED)
        
        # Calculate average processing time
        completed_with_time = [job for job in self.jobs.values() 
                             if job.status == ProcessingStatus.COMPLETED and job.processing_time]
        avg_processing_time = (sum(job.processing_time for job in completed_with_time) / 
                             len(completed_with_time)) if completed_with_time else 0
        
        # Most common errors
        common_errors = {}
        for job in self.jobs.values():
            if job.error_message:
                error_type = job.error_message.split(':')[0]
                common_errors[error_type] = common_errors.get(error_type, 0) + 1
        
        most_common_errors = sorted(common_errors.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_files_processed": total_jobs,
            "successful_conversions": completed_jobs,
            "failed_conversions": failed_jobs,
            "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
            "average_processing_time": avg_processing_time,
            "most_common_errors": [error[0] for error in most_common_errors],
            "ai_enabled": self.ai_analyzer.is_available,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old jobs to prevent memory issues."""
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        
        jobs_to_remove = []
        for job_id, job in self.jobs.items():
            if job.created_at.timestamp() < cutoff_time:
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.jobs[job_id]
            logger.info(f"Cleaned up old job: {job_id}")
        
        if jobs_to_remove:
            logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")