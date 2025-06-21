"""Enhanced EDI processing service with production-grade validation and error handling."""

import asyncio
import uuid
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from ..core.edi_parser import EDI278Parser, EDI278Validator, ProductionTR3Validator
from ..core.fhir_mapper import X12To278FHIRMapper, ProductionFHIRMapper, get_fhir_mapper
from ..core.models import (
    ParsedEDI, ValidationResult, FHIRMapping, AIAnalysis, ProcessingJob,
    EDIFileUpload, ProcessingStatus, ValidationLevel
)
from ..ai.analyzer import EDIAIAnalyzer, SmartEDIValidator
from ..core.logger import get_logger

logger = get_logger(__name__)


def safe_model_dump(obj) -> Dict[str, Any]:
    """Safely convert Pydantic model to dict with fallback."""
    try:
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        elif hasattr(obj, 'dict'):
            return obj.dict()
        else:
            return obj.__dict__ if hasattr(obj, '__dict__') else {}
    except Exception:
        return {}


class EDIProcessingError(Exception):
    """Custom exception for EDI processing errors."""
    pass


class ProductionEDIProcessingService:
    """
    Production-grade EDI processing service with strict TR3 compliance and comprehensive error handling.
    Implements industry-standard validation and processing workflows for healthcare EDI transactions.
    """
    
    def __init__(self):
        """Initialize production processing service with enhanced components."""
        # Core components with production enhancements
        self.parser = EDI278Parser()
        self.validator = EDI278Validator()  # Now uses ProductionTR3Validator internally
        self.production_validator = ProductionTR3Validator()  # Direct access for strict validation
        self.fhir_mapper = ProductionFHIRMapper()  # Production-grade FHIR mapper
        
        # AI components (optional but recommended)
        self.ai_analyzer = EDIAIAnalyzer()
        self.smart_validator = SmartEDIValidator(self.ai_analyzer) if self.ai_analyzer.is_available else None
        
        # Job tracking and statistics
        self.jobs: Dict[str, ProcessingJob] = {}
        self.processing_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'tr3_compliant': 0,
            'tr3_non_compliant': 0,
            'average_processing_time': 0.0,
            'last_reset': datetime.utcnow()
        }
        
        logger.info("Production EDI Processing Service initialized with strict TR3 compliance")
        logger.info(f"AI Analysis: {'enabled' if self.ai_analyzer.is_available else 'disabled'}")
        logger.info(f"Smart Validation: {'enabled' if self.smart_validator else 'disabled'}")

    async def process_content(self, content: str, upload_request: EDIFileUpload) -> ProcessingJob:
        """
        Process EDI content with production-grade validation and error handling.
        
        Args:
            content: EDI content string
            upload_request: Processing configuration
            
        Returns:
            ProcessingJob: Complete processing results with strict validation
        """
        job_id = str(uuid.uuid4())
        job = ProcessingJob(
            job_id=job_id,
            filename=upload_request.filename,
            status=ProcessingStatus.PENDING,
            file_size=len(content.encode('utf-8'))
        )
        
        self.jobs[job_id] = job
        
        try:
            logger.info(f"Starting production processing for job {job_id}")
            job.status = ProcessingStatus.PROCESSING
            job.started_at = datetime.utcnow()
            
            start_time = time.time()
            error_details = []
            
            # Phase 1: EDI Parsing with comprehensive error handling
            try:
                logger.info(f"[{job_id}] Phase 1: EDI Parsing")
                parsed_edi = await self._parse_edi_content_production(content, upload_request.filename)
                job.parsed_edi = parsed_edi
                logger.info(f"[{job_id}] ✅ Parsing successful: {len(parsed_edi.segments)} segments, method: {parsed_edi.parsing_method}")
            except Exception as e:
                error_msg = f"EDI parsing failed: {str(e)}"
                error_details.append(error_msg)
                logger.error(f"[{job_id}] ❌ {error_msg}")
                job.error_message = error_msg
                job.status = ProcessingStatus.FAILED
                job.completed_at = datetime.utcnow()
                self._update_stats(success=False, tr3_compliant=False)
                return job
            
            # Phase 2: Production-grade TR3 Validation
            try:
                logger.info(f"[{job_id}] Phase 2: Production TR3 Validation")
                validation_result = await self._validate_edi_production(parsed_edi, upload_request)
                job.validation_result = validation_result
                
                # Log validation results
                critical_issues = [i for i in validation_result.issues if i.level == ValidationLevel.CRITICAL]
                error_issues = [i for i in validation_result.issues if i.level == ValidationLevel.ERROR]
                
                logger.info(f"[{job_id}] Validation: Valid={validation_result.is_valid}, TR3={validation_result.tr3_compliance}")
                logger.info(f"[{job_id}] Issues: {len(validation_result.issues)} total, {len(critical_issues)} critical, {len(error_issues)} errors")
                
                # Production rule: Fail processing if critical issues exist
                if critical_issues:
                    error_msg = f"Production validation failed: {len(critical_issues)} critical TR3 compliance issues"
                    error_details.append(error_msg)
                    logger.error(f"[{job_id}] ❌ {error_msg}")
                    job.error_message = error_msg
                    job.status = ProcessingStatus.FAILED
                    job.completed_at = datetime.utcnow()
                    self._update_stats(success=False, tr3_compliant=False)
                    return job
                
            except Exception as e:
                error_msg = f"Production validation failed: {str(e)}"
                error_details.append(error_msg)
                logger.error(f"[{job_id}] ❌ {error_msg}")
                job.error_message = error_msg
                job.status = ProcessingStatus.FAILED
                job.completed_at = datetime.utcnow()
                self._update_stats(success=False, tr3_compliant=False)
                return job
            
            # Phase 3: AI Analysis (if enabled and available)
            if upload_request.enable_ai_analysis and self.ai_analyzer.is_available:
                try:
                    logger.info(f"[{job_id}] Phase 3: AI Analysis")
                    ai_analysis = await self._analyze_with_ai_production(parsed_edi, validation_result)
                    job.ai_analysis = ai_analysis
                    logger.info(f"[{job_id}] ✅ AI analysis completed: confidence={ai_analysis.confidence_score:.2f}, risk={ai_analysis.risk_assessment}")
                except Exception as e:
                    warning_msg = f"AI analysis failed: {str(e)}"
                    error_details.append(warning_msg)
                    logger.warning(f"[{job_id}] ⚠️ {warning_msg}")
                    # AI failure doesn't stop processing
            
            # Phase 4: FHIR Mapping (if not validation-only)
            if not upload_request.validate_only:
                try:
                    logger.info(f"[{job_id}] Phase 4: Production FHIR Mapping")
                    fhir_mapping = await self._map_to_fhir_production(parsed_edi)
                    job.fhir_mapping = fhir_mapping
                    logger.info(f"[{job_id}] ✅ FHIR mapping completed: {len(fhir_mapping.resources)} resources")
                except Exception as e:
                    warning_msg = f"FHIR mapping failed: {str(e)}"
                    error_details.append(warning_msg)
                    logger.warning(f"[{job_id}] ⚠️ {warning_msg}")
                    # FHIR failure doesn't stop processing if validation passed
            
            # Calculate processing time and determine final status
            processing_time = time.time() - start_time
            job.processing_time = processing_time
            job.completed_at = datetime.utcnow()
            
            # Determine final status based on production criteria
            if error_details:
                # Has warnings but no critical failures
                job.status = ProcessingStatus.COMPLETED
                job.error_message = f"Completed with {len(error_details)} warning(s): " + "; ".join(error_details[:3])
                logger.warning(f"[{job_id}] ⚠️ Processing completed with warnings")
            else:
                # Complete success
                job.status = ProcessingStatus.COMPLETED
                logger.info(f"[{job_id}] ✅ Processing completed successfully")
            
            # Update statistics
            is_success = job.status == ProcessingStatus.COMPLETED
            is_tr3_compliant = validation_result.tr3_compliance if validation_result else False
            self._update_stats(success=is_success, tr3_compliant=is_tr3_compliant, processing_time=processing_time)
            
            logger.info(f"[{job_id}] Final status: {job.status.value}, TR3 compliant: {is_tr3_compliant}, Time: {processing_time:.2f}s")
            
            return job
            
        except Exception as e:
            logger.error(f"[{job_id}] ❌ Unexpected processing error: {str(e)}")
            job.error_message = f"Processing system error: {str(e)}"
            job.status = ProcessingStatus.FAILED
            job.completed_at = datetime.utcnow()
            self._update_stats(success=False, tr3_compliant=False)
            return job

    async def _parse_edi_content_production(self, content: str, filename: str) -> ParsedEDI:
        """Production-grade EDI parsing with enhanced error handling."""
        try:
            # Run parsing in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            parsed_edi = await loop.run_in_executor(
                None, self.parser.parse_content, content, filename
            )
            
            # Validate parsing results
            if not parsed_edi.segments or len(parsed_edi.segments) == 0:
                raise EDIProcessingError("No segments were parsed from the EDI content")
            
            # Log parsing method and quality
            logger.info(f"Parsed {len(parsed_edi.segments)} segments using {parsed_edi.parsing_method}")
            
            # Warn if using fallback parsing
            if 'fallback' in parsed_edi.parsing_method.lower():
                logger.warning("Using fallback parsing - consider improving EDI format for optimal processing")
            
            return parsed_edi
            
        except Exception as e:
            logger.error(f"Production EDI parsing failed: {str(e)}")
            raise EDIProcessingError(f"Failed to parse EDI content: {str(e)}")

    async def _validate_edi_production(self, parsed_edi: ParsedEDI, upload_request: EDIFileUpload) -> ValidationResult:
        """Production-grade validation with strict TR3 compliance."""
        try:
            # Use production TR3 validator for strict compliance
            loop = asyncio.get_event_loop()
            validation_result = await loop.run_in_executor(
                None, self.production_validator.validate_strict_tr3_compliance, parsed_edi
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
            logger.error(f"Production validation failed: {str(e)}")
            raise EDIProcessingError(f"Failed to validate EDI: {str(e)}")

    async def _analyze_with_ai_production(self, parsed_edi: ParsedEDI, validation_result: ValidationResult) -> Optional[AIAnalysis]:
        """Production-grade AI analysis with enhanced error handling."""
        try:
            if not self.ai_analyzer.is_available:
                logger.info("AI analysis not available")
                return None
            
            ai_analysis = await self.ai_analyzer.analyze_edi(parsed_edi, validation_result)
            
            # Validate AI analysis results
            if ai_analysis.confidence_score < 0.0 or ai_analysis.confidence_score > 1.0:
                logger.warning(f"AI confidence score out of range: {ai_analysis.confidence_score}")
                ai_analysis.confidence_score = max(0.0, min(1.0, ai_analysis.confidence_score))
            
            return ai_analysis
            
        except Exception as e:
            logger.error(f"Production AI analysis failed: {str(e)}")
            # Return None instead of raising - AI failure shouldn't stop processing
            return None

    async def _map_to_fhir_production(self, parsed_edi: ParsedEDI) -> FHIRMapping:
        """Production-grade FHIR mapping with comprehensive error handling."""
        try:
            # Use production FHIR mapper
            loop = asyncio.get_event_loop()
            fhir_mapping = await loop.run_in_executor(
                None, self.fhir_mapper.map_to_fhir, parsed_edi
            )
            
            # Validate FHIR mapping results
            if not fhir_mapping.resources or len(fhir_mapping.resources) == 0:
                raise EDIProcessingError("No FHIR resources were created")
            
            logger.info(f"Successfully created {len(fhir_mapping.resources)} FHIR resources")
            return fhir_mapping
            
        except Exception as e:
            logger.error(f"Production FHIR mapping failed: {str(e)}")
            raise EDIProcessingError(f"Failed to map to FHIR: {str(e)}")

    def _update_stats(self, success: bool, tr3_compliant: bool, processing_time: float = 0.0):
        """Update processing statistics for monitoring and reporting."""
        try:
            self.processing_stats['total_processed'] += 1
            
            if success:
                self.processing_stats['successful'] += 1
            else:
                self.processing_stats['failed'] += 1
            
            if tr3_compliant:
                self.processing_stats['tr3_compliant'] += 1
            else:
                self.processing_stats['tr3_non_compliant'] += 1
            
            # Update average processing time
            if processing_time > 0:
                current_avg = self.processing_stats['average_processing_time']
                total = self.processing_stats['total_processed']
                new_avg = ((current_avg * (total - 1)) + processing_time) / total
                self.processing_stats['average_processing_time'] = new_avg
                
        except Exception as e:
            logger.warning(f"Failed to update statistics: {str(e)}")

    def get_production_statistics(self) -> Dict[str, Any]:
        """Get comprehensive production statistics."""
        try:
            total = self.processing_stats['total_processed']
            success_rate = (self.processing_stats['successful'] / total * 100) if total > 0 else 0
            tr3_compliance_rate = (self.processing_stats['tr3_compliant'] / total * 100) if total > 0 else 0
            
            return {
                **self.processing_stats,
                'success_rate': round(success_rate, 2),
                'tr3_compliance_rate': round(tr3_compliance_rate, 2),
                'active_jobs': len(self.jobs),
                'system_status': 'healthy' if success_rate >= 90 else 'degraded' if success_rate >= 70 else 'critical'
            }
        except Exception as e:
            logger.error(f"Failed to generate statistics: {str(e)}")
            return {'error': 'Statistics unavailable', 'total_processed': 0}

    async def validate_production_readiness(self) -> Dict[str, Any]:
        """Validate system production readiness with comprehensive checks."""
        try:
            readiness_report = {
                'overall_status': 'unknown',
                'components': {},
                'recommendations': [],
                'blocking_issues': []
            }
            
            # Check core components
            try:
                # Test parser
                test_content = "ISA*00*          *00*          *ZZ*SENDER*ZZ*RECEIVER*250620*1909*U*00501*000000001*0*P*>~GS*HS*SENDER*RECEIVER*20250620*1909*1*X*005010X279A1~ST*278*0001~BHT*0078*00*REF123*20250620*1909*01~SE*4*0001~GE*1*1~IEA*1*000000001~"
                parsed = self.parser.parse_content(test_content, "test.edi")
                readiness_report['components']['parser'] = 'operational'
            except Exception as e:
                readiness_report['components']['parser'] = f'failed: {str(e)}'
                readiness_report['blocking_issues'].append('Parser component failure')
            
            # Test validator
            try:
                if 'parser' in readiness_report['components'] and readiness_report['components']['parser'] == 'operational':
                    validation = self.production_validator.validate_strict_tr3_compliance(parsed)
                    readiness_report['components']['validator'] = 'operational'
                else:
                    readiness_report['components']['validator'] = 'skipped - parser failed'
            except Exception as e:
                readiness_report['components']['validator'] = f'failed: {str(e)}'
                readiness_report['blocking_issues'].append('Validator component failure')
            
            # Test FHIR mapper
            try:
                if 'parser' in readiness_report['components'] and readiness_report['components']['parser'] == 'operational':
                    fhir_result = self.fhir_mapper.map_to_fhir(parsed)
                    readiness_report['components']['fhir_mapper'] = 'operational'
                else:
                    readiness_report['components']['fhir_mapper'] = 'skipped - parser failed'
            except Exception as e:
                readiness_report['components']['fhir_mapper'] = f'failed: {str(e)}'
                readiness_report['blocking_issues'].append('FHIR mapper component failure')
            
            # Test AI analyzer
            readiness_report['components']['ai_analyzer'] = 'operational' if self.ai_analyzer.is_available else 'disabled'
            
            # Determine overall status
            operational_components = sum(1 for status in readiness_report['components'].values() if status == 'operational')
            total_critical_components = 3  # parser, validator, fhir_mapper
            
            if len(readiness_report['blocking_issues']) == 0 and operational_components >= total_critical_components:
                readiness_report['overall_status'] = 'production_ready'
            elif operational_components >= 2:
                readiness_report['overall_status'] = 'limited_operation'
                readiness_report['recommendations'].append('Some components not operational - limited functionality')
            else:
                readiness_report['overall_status'] = 'not_ready'
                readiness_report['recommendations'].append('Critical component failures prevent production deployment')
            
            return readiness_report
            
        except Exception as e:
            logger.error(f"Production readiness check failed: {str(e)}")
            return {
                'overall_status': 'check_failed',
                'error': str(e),
                'blocking_issues': ['Production readiness check system failure']
            }

    async def export_results(self, job_id: str, format: str) -> Optional[str]:
        """
        Export job results in specified format with comprehensive error handling.
        
        Args:
            job_id: Job identifier
            format: Export format (json, xml, edi, validation)
            
        Returns:
            Exported content as string or None if job not found
            
        Raises:
            EDIProcessingError: If export fails or format not supported
        """
        try:
            # Get job
            if job_id not in self.jobs:
                return None
            
            job = self.jobs[job_id]
            
            if format == "json":
                # Export complete job data as JSON
                job_data = {
                    "job_id": job.job_id,
                    "filename": job.filename,
                    "status": job.status.value,
                    "created_at": job.created_at.isoformat(),
                    "processing_time": job.processing_time,
                    "validation_result": safe_model_dump(job.validation_result) if job.validation_result else None,
                    "fhir_mapping": safe_model_dump(job.fhir_mapping) if job.fhir_mapping else None,
                    "ai_analysis": safe_model_dump(job.ai_analysis) if job.ai_analysis else None
                }
                return json.dumps(job_data, indent=2, default=str)
                
            elif format == "xml":
                # Export FHIR resources as XML
                if not job.fhir_mapping or not job.fhir_mapping.resources:
                    raise EDIProcessingError("No FHIR mapping available for XML export")
                
                # Convert FHIR resources to XML format
                try:
                    import xml.etree.ElementTree as ET
                    
                    # Create root element
                    root = ET.Element("Bundle")
                    root.set("xmlns", "http://hl7.org/fhir")
                    
                    # Add metadata
                    meta = ET.SubElement(root, "meta")
                    profile = ET.SubElement(meta, "profile")
                    profile.set("value", "http://hl7.org/fhir/us/davinci-pas/StructureDefinition/profile-pas-request-bundle")
                    
                    # Add resources
                    for resource in job.fhir_mapping.resources:
                        entry = ET.SubElement(root, "entry")
                        resource_element = ET.SubElement(entry, "resource")
                        
                        # Add resource type
                        res_type = ET.SubElement(resource_element, resource.resource_type)
                        res_type.set("xmlns", "http://hl7.org/fhir")
                        
                        # Add resource ID
                        if resource.id:
                            id_elem = ET.SubElement(res_type, "id")
                            id_elem.set("value", resource.id)
                        
                        # Add basic resource data (simplified XML conversion)
                        for key, value in resource.data.items():
                            if key not in ['resourceType', 'id'] and isinstance(value, (str, int, float, bool)):
                                elem = ET.SubElement(res_type, key)
                                elem.set("value", str(value))
                    
                    # Convert to string
                    return ET.tostring(root, encoding='unicode', method='xml')
                    
                except Exception as xml_error:
                    logger.error(f"XML conversion failed: {xml_error}")
                    raise EDIProcessingError(f"Failed to convert FHIR to XML: {str(xml_error)}")
                
            elif format == "edi":
                # Export original or processed EDI content
                if job.parsed_edi and job.parsed_edi.raw_content:
                    return job.parsed_edi.raw_content
                else:
                    raise EDIProcessingError("No EDI content available for export")
                    
            elif format == "validation":
                # Export validation report
                if not job.validation_result:
                    raise EDIProcessingError("No validation results available")
                
                validation_report = {
                    "job_id": job.job_id,
                    "filename": job.filename,
                    "validation_summary": {
                        "is_valid": job.validation_result.is_valid,
                        "tr3_compliance": job.validation_result.tr3_compliance,
                        "segments_validated": job.validation_result.segments_validated,
                        "validation_time": job.validation_result.validation_time
                    },
                    "issues": [
                        {
                            "level": issue.level.value if hasattr(issue.level, 'value') else str(issue.level),
                            "code": issue.code,
                            "message": issue.message,
                            "segment": issue.segment,
                            "line_number": issue.line_number,
                            "suggested_fix": issue.suggested_fix
                        }
                        for issue in job.validation_result.issues
                    ],
                    "suggested_improvements": job.validation_result.suggested_improvements,
                    "generated_at": datetime.utcnow().isoformat()
                }
                return json.dumps(validation_report, indent=2, default=str)
                
            else:
                raise EDIProcessingError(f"Unsupported export format: {format}")
                
        except EDIProcessingError:
            # Re-raise EDI processing errors
            raise
        except Exception as e:
            logger.error(f"Export failed for job {job_id}: {str(e)}")
            raise EDIProcessingError(f"Export failed: {str(e)}")

    def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get job by ID."""
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> Dict[str, ProcessingJob]:
        """Get all jobs."""
        return self.jobs.copy()

    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old jobs."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            jobs_to_remove = [
                job_id for job_id, job in self.jobs.items()
                if job.created_at < cutoff_time
            ]
            
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
                
            logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")
            
        except Exception as e:
            logger.error(f"Job cleanup failed: {str(e)}")


# Maintain compatibility with existing code
class EDIProcessingService(ProductionEDIProcessingService):
    """Compatibility alias for existing code."""
    pass