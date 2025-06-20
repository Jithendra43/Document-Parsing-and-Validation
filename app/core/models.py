"""Core data models for EDI processing and validation."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class EDITransactionType(str, Enum):
    """Supported EDI transaction types."""
    REQUEST_278 = "278"
    RESPONSE_278 = "278"


class ValidationLevel(str, Enum):
    """Validation severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ProcessingStatus(str, Enum):
    """Processing status for EDI files."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationIssue(BaseModel):
    """Individual validation issue."""
    level: ValidationLevel
    code: str
    message: str
    segment: Optional[str] = None
    element: Optional[str] = None
    line_number: Optional[int] = None
    suggested_fix: Optional[str] = None


class EDIHeader(BaseModel):
    """EDI file header information."""
    isa_control_number: str
    gs_control_number: str
    st_control_number: str
    transaction_type: str
    version: str
    sender_id: str
    receiver_id: str
    interchange_date: Optional[datetime] = None


class EDISegment(BaseModel):
    """Enhanced EDI segment representation with X12 278 loop tracking."""
    segment_id: str  # Changed from 'tag' for clarity
    elements: List[str]
    position: int = Field(description="Segment position in file")
    loop_id: Optional[str] = Field(None, description="X12 278 loop identifier (2000A, 2000B, etc.)")
    hl_level: Optional[int] = Field(None, description="Hierarchical level from HL segment")
    
    # Legacy support
    @property
    def tag(self) -> str:
        """Legacy property for backward compatibility."""
        return self.segment_id
    
    @property 
    def line_number(self) -> int:
        """Legacy property for backward compatibility."""
        return self.position


class ParsedEDI(BaseModel):
    """Parsed EDI document structure."""
    header: EDIHeader
    segments: List[EDISegment]
    raw_content: str
    file_size: int
    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    parsing_method: Optional[str] = Field(None, description="Method used for parsing: pyx12, manual_fallback, etc.")


class ValidationResult(BaseModel):
    """EDI validation result."""
    is_valid: bool
    issues: List[ValidationIssue] = []
    segments_validated: int = 0
    validation_time: float = 0.0
    tr3_compliance: bool = True
    suggested_improvements: List[str] = []


class FHIRResource(BaseModel):
    """FHIR resource representation."""
    resource_type: str
    id: Optional[str] = None
    data: Dict[str, Any]


class FHIRMapping(BaseModel):
    """FHIR mapping result."""
    resources: List[FHIRResource] = []
    mapping_version: str = "1.0"
    mapped_at: datetime = Field(default_factory=datetime.utcnow)
    source_segments: List[str] = []


class AIAnalysis(BaseModel):
    """AI-powered analysis results."""
    anomalies_detected: List[str] = []
    confidence_score: float = Field(ge=0.0, le=1.0)
    suggested_fixes: List[str] = []
    pattern_analysis: Dict[str, Any] = {}
    risk_assessment: str = "low"  # low, medium, high


class ProcessingJob(BaseModel):
    """Processing job tracking."""
    job_id: str
    filename: str
    status: ProcessingStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Processing results
    parsed_edi: Optional[ParsedEDI] = None
    validation_result: Optional[ValidationResult] = None
    fhir_mapping: Optional[FHIRMapping] = None
    ai_analysis: Optional[AIAnalysis] = None
    
    # Metrics
    processing_time: Optional[float] = None
    file_size: Optional[int] = None


class EDIFileUpload(BaseModel):
    """EDI file upload request."""
    filename: str
    content_type: str = "text/plain"
    validate_only: bool = False
    enable_ai_analysis: bool = True
    output_format: str = "fhir"  # fhir, xml, json


class EDIProcessingResponse(BaseModel):
    """EDI processing response."""
    job_id: str
    status: ProcessingStatus
    message: str
    download_url: Optional[str] = None
    validation_summary: Optional[Dict[str, Any]] = None


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "0.1.0"
    components: Dict[str, str] = {}


class EDIStatistics(BaseModel):
    """EDI processing statistics."""
    total_files_processed: int = 0
    successful_conversions: int = 0
    failed_conversions: int = 0
    average_processing_time: float = 0.0
    most_common_errors: List[str] = []
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# Enhanced models for FHIR mapping and X12 278 processing

class EDI278Segment(BaseModel):
    """Specific model for X12 278 segments with enhanced tracking."""
    segment_id: str
    elements: List[str]
    position: int
    loop_id: Optional[str] = None
    hl_level: Optional[int] = None
    is_required: bool = True
    tr3_validation_status: Optional[str] = None


class EDI278ParsedData(BaseModel):
    """Parsed X12 278 EDI data with enhanced structure."""
    header: EDIHeader
    segments: List[EDI278Segment]
    loops_detected: Dict[str, List[str]] = Field(default_factory=dict)
    hl_hierarchy: Dict[str, Any] = Field(default_factory=dict)
    raw_content: str
    file_size: int
    parsed_at: datetime = Field(default_factory=datetime.utcnow)
    pyx12_version: Optional[str] = None
    tr3_compliance_level: Optional[str] = None


class FHIRMappingResult(BaseModel):
    """Result of FHIR mapping operation."""
    fhir_bundle: Dict[str, Any]
    resource_count: int
    mapping_warnings: List[str] = []
    is_valid: bool = True
    fhir_version: str = "R4"
    profile_compliance: List[str] = []
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class X12ValidationRule(BaseModel):
    """X12 TR3 validation rule."""
    rule_id: str
    segment_id: str
    element_position: Optional[int] = None
    required: bool = True
    data_type: str
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    valid_values: Optional[List[str]] = None
    description: str


class TR3ComplianceResult(BaseModel):
    """TR3 compliance validation result."""
    is_compliant: bool
    version: str = "005010X217"
    violations: List[ValidationIssue] = []
    compliance_score: float = Field(ge=0.0, le=1.0)
    recommendations: List[str] = []
    validated_at: datetime = Field(default_factory=datetime.utcnow) 