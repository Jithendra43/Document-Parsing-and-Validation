"""Enhanced EDI X12 278 parser with robust error handling and fallback mechanisms."""

import re
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from .models import ParsedEDI, EDIHeader, EDISegment, ValidationResult, ValidationIssue, ValidationLevel
from .logger import get_logger

# Initialize logger first
logger = get_logger(__name__)

# Try to import pyx12 components
HAS_PYX12 = True
pyx12 = None
X12Reader = None

try:
    import pyx12
    import pyx12.error_handler
    import pyx12.x12file
    import pyx12.x12n_document
    import pyx12.x12context
    import pyx12.params
    import pyx12.map_if
    from pyx12.x12file import X12Reader
except ImportError as e:
    HAS_PYX12 = False
    pyx12 = None
    X12Reader = None
    # Create dummy objects to prevent NameError
    class DummyPyX12:
        pass
    pyx12 = DummyPyX12()
    X12Reader = None

from ..config import settings

# Get logger after all imports
logger = get_logger(__name__)

# Log pyx12 status after logger is available
if HAS_PYX12:
    logger.info("✅ pyx12 library available")
else:
    logger.warning("pyx12 not available - will use manual parsing fallback")


class EDIParsingError(Exception):
    """Custom exception for EDI parsing errors."""
    pass


class EDI278Parser:
    """Enhanced EDI X12 278 parser with multiple parsing strategies."""
    
    def __init__(self):
        """Initialize parser with configuration."""
        self.max_segments = 1000  # Safety limit
        logger.info("EDI278Parser initialized")
    
    def parse_file(self, file_path: str) -> ParsedEDI:
        """
        Parse EDI file from filesystem.
        
        Args:
            file_path: Path to EDI file
            
        Returns:
            ParsedEDI: Parsed EDI structure
            
        Raises:
            EDIParsingError: If parsing fails completely
        """
        try:
            logger.info(f"Parsing EDI file: {file_path}")
            
            # Read file content
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise EDIParsingError(f"File not found: {file_path}")
            
            content = file_path_obj.read_text(encoding='utf-8')
            file_size = file_path_obj.stat().st_size
            
            # Parse content
            result = self._parse_content_robust(content)
            
            # Create header
            header = self._extract_header_from_segments(result['segments'])
            
            # Convert to EDI segments
            edi_segments = self._convert_to_edi_segments(result['segments'])
            
            logger.info(f"✅ Successfully parsed {len(edi_segments)} segments using {result.get('method', 'unknown')} method")
            
            return ParsedEDI(
                header=header,
                segments=edi_segments,
                raw_content=content,
                file_size=file_size,
                parsing_method=result.get('method', 'unknown')
            )
            
        except Exception as e:
            logger.error(f"Failed to parse EDI file {file_path}: {str(e)}")
            raise EDIParsingError(f"Failed to parse EDI file: {str(e)}")
    
    def parse_content(self, content: str, filename: str = "content.edi") -> ParsedEDI:
        """
        Parse EDI content from string.
        
        Args:
            content: EDI content string
            filename: Filename for reference
            
        Returns:
            ParsedEDI: Parsed EDI structure
            
        Raises:
            EDIParsingError: If parsing fails completely
        """
        try:
            logger.info(f"Parsing EDI content from {filename}")
            
            if not content.strip():
                raise EDIParsingError("Empty content provided")
            
            # Parse content using robust method
            result = self._parse_content_robust(content)
            
            # Create header
            header = self._extract_header_from_segments(result['segments'])
            
            # Convert to EDI segments
            edi_segments = self._convert_to_edi_segments(result['segments'])
            
            logger.info(f"✅ Successfully parsed {len(edi_segments)} segments using {result.get('method', 'unknown')} method")
            
            return ParsedEDI(
                header=header,
                segments=edi_segments,
                raw_content=content,
                file_size=len(content.encode('utf-8')),
                parsing_method=result.get('method', 'unknown')
            )
            
        except Exception as e:
            logger.error(f"Failed to parse EDI content: {str(e)}")
            raise EDIParsingError(f"Failed to parse EDI content: {str(e)}")
    
    def _parse_content_robust(self, content: str) -> Dict[str, Any]:
        """
        Robust parsing with multiple fallback strategies.
        
        1. Enhanced pyx12 parsing (preferred)
        2. Simple pyx12 parsing
        3. Manual regex parsing (fallback)
        """
        parsing_methods = [
            ("pyx12_enhanced", self._parse_with_pyx12),
            ("pyx12_simple", self._parse_with_pyx12_simple),
            ("manual_fallback", self._parse_manually)
        ]
        
        for method_name, method in parsing_methods:
            try:
                logger.info(f"Attempting {method_name} parsing...")
                result = method(content)
                if result and result.get('segments'):
                    result['method'] = method_name
                    logger.info(f"✅ {method_name} parsing successful: {len(result['segments'])} segments")
                    return result
                else:
                    logger.warning(f"⚠️ {method_name} parsing returned no segments")
            except Exception as e:
                logger.warning(f"❌ {method_name} parsing failed: {str(e)}")
                continue
        
        raise EDIParsingError("All parsing methods failed")
    
    def _parse_with_pyx12(self, content: str) -> Dict[str, Any]:
        """Enhanced pyx12 parsing with proper error handling."""
        if not HAS_PYX12:
            raise EDIParsingError("pyx12 library not available")
        
        try:
            from io import StringIO
            
            # Pre-process content to handle common ISA version issues
            processed_content = self._preprocess_edi_content(content)
            
            # Create string buffer for content
            fd_in = StringIO(processed_content.strip())
            
            # Initialize pyx12 components with better error handling
            try:
                # Import specific modules
                from pyx12 import x12file, error_handler
                
                # Try to use X12Reader from pyx12
                if hasattr(x12file, 'X12Reader'):
                    src = x12file.X12Reader(fd_in)
                else:
                    raise AttributeError("X12Reader not available in pyx12.x12file")
                
                # Try to initialize error handler
                if hasattr(error_handler, 'ErrorHandler'):
                    errh = error_handler.ErrorHandler()
                elif hasattr(error_handler, 'err_handler'):
                    errh = error_handler.err_handler()
                else:
                    # Create minimal error handler
                    errh = type('ErrorHandler', (), {'err_list': []})()
                
            except Exception as init_error:
                logger.error(f"Enhanced pyx12 parsing error: {init_error}")
                # Check for specific pyx12 issues and provide better error handling
                error_msg = str(init_error)
                if "ISA Interchange Control Version Number is unknown" in error_msg:
                    logger.warning("pyx12 ISA control version issue - falling back to manual parsing")
                    raise EDIParsingError(f"pyx12 ISA version incompatibility: {init_error}")
                elif "No segments processed by pyx12" in error_msg:
                    logger.warning("pyx12 unable to process segments - falling back to manual parsing")
                    raise EDIParsingError(f"pyx12 segment processing failed: {init_error}")
                else:
                    raise EDIParsingError(f"Enhanced pyx12 parsing failed: {init_error}")
            
            # Parse segments using pyx12
            segments = []
            segment_position = 0
            pyx12_errors = []
            
            # Use iterator pattern for X12Reader
            try:
                # Different approaches for segment iteration
                if hasattr(src, '__iter__'):
                    # Modern pyx12 with iterator support
                    for seg in src:
                        segment_position += 1
                        if seg and hasattr(seg, 'get_id'):
                            segments.append(self._process_pyx12_segment(seg, segment_position))
                        
                        if segment_position >= self.max_segments:
                            logger.warning(f"Reached maximum segment limit: {self.max_segments}")
                            break
                            
                elif hasattr(src, 'next'):
                    # Legacy pyx12 with next() method
                    while True:
                        try:
                            seg = src.next()
                            if not seg:
                                break
                            segment_position += 1
                            if hasattr(seg, 'get_id'):
                                segments.append(self._process_pyx12_segment(seg, segment_position))
                        except StopIteration:
                            break
                        except Exception as e:
                            logger.warning(f"Error reading segment at position {segment_position}: {e}")
                            break
                            
                        if segment_position >= self.max_segments:
                            break
                else:
                    raise AttributeError("No valid iteration method found for X12Reader")
                    
            except Exception as iter_error:
                logger.error(f"Error during pyx12 iteration: {iter_error}")
                # Fall back to simple parsing if iteration fails
                raise EDIParsingError(f"pyx12 iteration failed: {iter_error}")
            
            # Check for pyx12 validation errors
            if hasattr(errh, 'err_list'):
                for error in errh.err_list:
                    if hasattr(error, 'msg'):
                        pyx12_errors.append(str(error.msg))
                    else:
                        pyx12_errors.append(str(error))
            
            if not segments:
                raise EDIParsingError("No segments processed by pyx12")
            
            return {
                'segments': segments,
                'pyx12_errors': pyx12_errors,
                'segment_count': len(segments)
            }
            
        except Exception as e:
            logger.error(f"pyx12 parsing error: {str(e)}")
            raise EDIParsingError(f"pyx12 parsing failed: {str(e)}")
    
    def _preprocess_edi_content(self, content: str) -> str:
        """Pre-process EDI content to handle common compatibility issues."""
        try:
            # Handle ISA version compatibility issues
            lines = content.strip().split('\n')
            processed_lines = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('ISA*'):
                    # Check and fix ISA version format
                    parts = line.split('*')
                    if len(parts) >= 12:
                        # ISA12 is the version number - ensure it's in correct format
                        version = parts[11]
                        # Common version mappings for compatibility
                        version_map = {
                            '00501': '00401',  # Map 5010 to 4010 for pyx12 compatibility
                            '501': '00401',
                            '5010': '00401'
                        }
                        if version in version_map:
                            parts[11] = version_map[version]
                            line = '*'.join(parts)
                            logger.debug(f"Mapped ISA version {version} to {version_map[version]} for pyx12 compatibility")
                
                processed_lines.append(line)
            
            return '\n'.join(processed_lines)
            
        except Exception as e:
            logger.warning(f"EDI preprocessing failed: {e}, using original content")
            return content
    
    def _process_pyx12_segment(self, seg, position: int) -> Dict[str, Any]:
        """Process a pyx12 segment object into our format."""
        try:
            segment_id = seg.get_id() if hasattr(seg, 'get_id') else 'UNK'
            elements = []
            
            # Extract elements from pyx12 segment
            try:
                if hasattr(seg, 'get_count'):
                    element_count = seg.get_count()
                    for i in range(1, element_count + 1):
                        element_value = seg.get_value(f"{segment_id}{i:02d}")
                        if element_value:
                            elements.append(element_value)
                elif hasattr(seg, 'get_elements'):
                    elements = seg.get_elements()
                else:
                    # Fallback: try to convert segment to string and parse
                    seg_str = str(seg)
                    if '*' in seg_str:
                        elements = seg_str.split('*')[1:]  # Skip segment ID
            except Exception as elem_error:
                logger.debug(f"Element extraction error for {segment_id}: {elem_error}")
                # Try string parsing as fallback
                seg_str = str(seg)
                if '*' in seg_str:
                    elements = seg_str.split('*')[1:]
            
            return {
                'tag': segment_id,
                'elements': elements,
                'raw': str(seg),
                'position': position,
                'pyx12_validated': True
            }
            
        except Exception as e:
            logger.warning(f"Error processing pyx12 segment at position {position}: {e}")
            return {
                'tag': 'ERR',
                'elements': [],
                'raw': str(seg) if seg else '',
                'position': position,
                'pyx12_validated': False
            }
    
    def _parse_with_pyx12_simple(self, content: str) -> Dict[str, Any]:
        """
        Simple pyx12 parsing method using basic functionality.
        """
        if not HAS_PYX12:
            raise EDIParsingError("pyx12 library not available")
        
        try:
            from io import StringIO
            
            # Create string buffer for content
            content_buffer = StringIO(content.strip())
            
            # Initialize X12Reader with error handling
            try:
                from pyx12 import x12file
                
                if hasattr(x12file, 'X12Reader'):
                    x12_reader = x12file.X12Reader(content_buffer)
                else:
                    logger.warning("Could not initialize X12Reader: pyx12.x12file.X12Reader not available")
                    raise AttributeError("X12Reader not available")
            except Exception as init_error:
                logger.warning(f"Could not initialize X12Reader: {init_error}")
                raise EDIParsingError(f"X12Reader initialization failed: {init_error}")
            
            segments = []
            segment_count = 0
            
            try:
                # Use iterator pattern for reading segments
                for segment in x12_reader:
                    if segment:
                        segment_count += 1
                        
                        # Convert segment to string and parse manually
                        segment_str = str(segment).strip()
                        if segment_str and '*' in segment_str:
                            parts = segment_str.split('*')
                            tag = parts[0] if parts else 'UNK'
                            elements = parts[1:] if len(parts) > 1 else []
                            
                            # Clean up elements (remove ~ and other terminators)
                            cleaned_elements = []
                            for elem in elements:
                                cleaned = elem.rstrip('~').strip()
                                if cleaned:
                                    cleaned_elements.append(cleaned)
                            
                            segments.append({
                                'tag': tag,
                                'elements': cleaned_elements,
                                'raw': segment_str,
                                'position': segment_count
                            })
                            
                            logger.debug(f"Simple pyx12 parsed: {tag} with {len(cleaned_elements)} elements")
                    
                    if segment_count >= self.max_segments:
                        logger.warning(f"Reached segment limit: {self.max_segments}")
                        break
                        
            except Exception as read_error:
                logger.warning(f"Error reading segment at position {segment_count}: {read_error}")
                # If we have some segments, continue with what we have
                if segments:
                    logger.info(f"Partial parsing successful: {len(segments)} segments")
                else:
                    raise EDIParsingError(f"Failed to read any segments: {read_error}")
            
            if not segments:
                logger.warning("❌ pyx12 parsing failed: No segments processed by pyx12")
                raise EDIParsingError("No segments processed by pyx12")
            
            return {
                'segments': segments,
                'segment_count': len(segments)
            }
            
        except Exception as e:
            logger.error(f"Simple pyx12 parsing error: {str(e)}")
            raise EDIParsingError(f"Simple pyx12 parsing failed: {str(e)}")
    
    def _parse_manually(self, content: str) -> Dict[str, Any]:
        """
        Manual parsing using regex patterns as ultimate fallback.
        This method handles damaged or non-standard EDI files.
        """
        try:
            logger.info("Using manual parsing fallback")
            
            # Split content into segments by various terminators
            content = content.strip()
            
            # Try different segment separators
            separators = ['~', '\n', '\r\n']
            segments_raw = []
            
            for sep in separators:
                if sep in content:
                    segments_raw = [s.strip() for s in content.split(sep) if s.strip()]
                    break
            
            if not segments_raw:
                # If no separators found, treat as single segment
                segments_raw = [content]
            
            segments = []
            position = 0
            
            for segment_raw in segments_raw:
                position += 1
                
                if not segment_raw or len(segment_raw) < 2:
                    continue
                
                # Parse segment manually
                if '*' in segment_raw:
                    parts = segment_raw.split('*')
                    tag = parts[0].strip()
                    elements = [elem.strip() for elem in parts[1:] if elem.strip()]
                    
                    # Validate segment tag (should be 2-3 letters/numbers)
                    if len(tag) >= 2 and tag.isalnum():
                        segments.append({
                            'tag': tag,
                            'elements': elements,
                            'raw': segment_raw,
                            'position': position
                        })
                        
                        logger.debug(f"Manual parsed: {tag} with {len(elements)} elements")
                else:
                    # Handle segments without '*' (malformed but try to salvage)
                    cleaned_segment = segment_raw.strip()
                    if len(cleaned_segment) >= 2:
                        # Try to extract at least a segment ID
                        tag = cleaned_segment[:3] if len(cleaned_segment) >= 3 else cleaned_segment
                        if tag.isalnum():
                            segments.append({
                                'tag': tag,
                                'elements': [],
                                'raw': segment_raw,
                                'position': position
                            })
                            logger.debug(f"Manual parsed malformed: {tag}")
                
                if position >= self.max_segments:
                    logger.warning(f"Reached manual parsing segment limit: {self.max_segments}")
                    break
            
            if not segments:
                raise EDIParsingError("Manual parsing produced no valid segments")
            
            logger.info(f"✅ Manual parsing successful: {len(segments)} segments")
            
            return {
                'segments': segments,
                'segment_count': len(segments)
            }
            
        except Exception as e:
            logger.error(f"Manual parsing failed: {str(e)}")
            raise EDIParsingError(f"Manual parsing failed: {str(e)}")
    
    def _convert_to_edi_segments(self, raw_segments: List[Dict[str, Any]]) -> List[EDISegment]:
        """Convert raw segment data to EDISegment objects."""
        edi_segments = []
        
        for seg_data in raw_segments:
            try:
                # Determine loop_id and hl_level for X12 278 structure
                loop_id = None
                hl_level = None
                
                segment_id = seg_data.get('tag', '')
                elements = seg_data.get('elements', [])
                position = seg_data.get('position', 0)
                
                # Detect X12 278 loops based on segment patterns
                if segment_id == 'HL' and len(elements) >= 3:
                    try:
                        hl_level = int(elements[0])
                        level_code = elements[2] if len(elements) > 2 else ''
                        
                        # Map HL level codes to loop IDs for X12 278
                        level_map = {
                            '20': '2000A',  # Information Source
                            '21': '2000B',  # Information Receiver  
                            '22': '2000C',  # Subscriber
                            '23': '2000D'   # Dependent
                        }
                        loop_id = level_map.get(level_code)
                        
                    except (ValueError, IndexError):
                        pass
                
                # Create EDISegment
                edi_segment = EDISegment(
                    segment_id=segment_id,
                    elements=elements,
                    position=position,
                    loop_id=loop_id,
                    hl_level=hl_level
                )
                
                edi_segments.append(edi_segment)
                
            except Exception as e:
                logger.warning(f"Error converting segment at position {seg_data.get('position', 0)}: {e}")
                # Create minimal segment to avoid data loss
                edi_segments.append(EDISegment(
                    segment_id=seg_data.get('tag', 'ERR'),
                    elements=seg_data.get('elements', []),
                    position=seg_data.get('position', 0)
                ))
        
        return edi_segments
    
    def _extract_header_from_segments(self, raw_segments: List[Dict[str, Any]]) -> EDIHeader:
        """Extract EDI header information from segments."""
        try:
            # Find ISA, GS, and ST segments
            isa_segment = None
            gs_segment = None
            st_segment = None
            
            for seg in raw_segments:
                tag = seg.get('tag', '')
                if tag == 'ISA':
                    isa_segment = seg
                elif tag == 'GS':
                    gs_segment = seg
                elif tag == 'ST':
                    st_segment = seg
                    break  # ST comes after ISA and GS
            
            # Extract control numbers and IDs
            isa_control = isa_segment['elements'][12] if isa_segment and len(isa_segment['elements']) > 12 else "000000001"
            gs_control = gs_segment['elements'][5] if gs_segment and len(gs_segment['elements']) > 5 else "1"
            st_control = st_segment['elements'][1] if st_segment and len(st_segment['elements']) > 1 else "0001"
            
            # Transaction type (from ST segment)
            transaction_type = st_segment['elements'][0] if st_segment and len(st_segment['elements']) > 0 else "278"
            
            # Version information
            version = "005010X279A1"  # X12 278 version
            if gs_segment and len(gs_segment['elements']) > 7:
                version = gs_segment['elements'][7]
            
            # Sender and Receiver IDs from ISA
            sender_id = "UNKNOWN"
            receiver_id = "UNKNOWN"
            
            if isa_segment and len(isa_segment['elements']) >= 10:
                sender_id = isa_segment['elements'][5].strip()
                receiver_id = isa_segment['elements'][7].strip()
            
            # Parse interchange date/time
            interchange_date = None
            if isa_segment and len(isa_segment['elements']) >= 10:
                try:
                    date_str = isa_segment['elements'][8]  # YYMMDD
                    time_str = isa_segment['elements'][9]  # HHMM
                    
                    if len(date_str) == 6 and len(time_str) == 4:
                        # Convert YY to YYYY (assuming 20XX for years 00-29, 19XX for 30-99)
                        yy = int(date_str[:2])
                        yyyy = 2000 + yy if yy <= 29 else 1900 + yy
                        
                        date_time_str = f"{yyyy}{date_str[2:]}{time_str}"
                        interchange_date = datetime.strptime(date_time_str, "%Y%m%d%H%M")
                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not parse interchange date/time: {e}")
            
            return EDIHeader(
                isa_control_number=isa_control,
                gs_control_number=gs_control,
                st_control_number=st_control,
                transaction_type=transaction_type,
                version=version,
                sender_id=sender_id,
                receiver_id=receiver_id,
                interchange_date=interchange_date
            )
            
        except Exception as e:
            logger.warning(f"Error extracting header: {e}")
            # Return minimal header
            return EDIHeader(
                isa_control_number="000000001",
                gs_control_number="1",
                st_control_number="0001",
                transaction_type="278",
                version="005010X279A1",
                sender_id="UNKNOWN",
                receiver_id="UNKNOWN"
            )


class EDI278Validator:
    """X12 278 specific validator with TR3 compliance checking."""
    
    def __init__(self):
        """Initialize validator."""
        logger.info("EDI278Validator initialized")
    
    def validate(self, parsed_edi: ParsedEDI) -> ValidationResult:
        """
        Comprehensive validation of X12 278 EDI document.
        
        Args:
            parsed_edi: Parsed EDI structure
            
        Returns:
            ValidationResult: Comprehensive validation results
        """
        try:
            start_time = time.time()
            logger.info(f"Starting validation of {len(parsed_edi.segments)} segments")
            
            issues = []
            
            # 1. Structural validation
            structural_issues = self._validate_structure(parsed_edi)
            issues.extend(structural_issues)
            
            # 2. Segment-level validation
            segment_issues = self._validate_segments(parsed_edi)
            issues.extend(segment_issues)
            
            # 3. TR3 compliance validation
            tr3_issues = self._validate_tr3_compliance(parsed_edi)
            issues.extend(tr3_issues)
            
            # Calculate overall validity - only CRITICAL issues prevent processing
            critical_issues = [issue for issue in issues if issue.level == ValidationLevel.CRITICAL]
            error_issues = [issue for issue in issues if issue.level == ValidationLevel.ERROR]
            
            # Document is valid if no critical issues and major structure is intact
            is_valid = len(critical_issues) == 0
            
            # TR3 compliance is stricter - no errors or warnings in TR3 validation
            tr3_error_issues = [issue for issue in tr3_issues if issue.level in [ValidationLevel.CRITICAL, ValidationLevel.ERROR]]
            tr3_compliance = len(tr3_error_issues) == 0
            
            # Generate improvement suggestions
            suggestions = self._generate_suggestions(issues)
            
            validation_time = time.time() - start_time
            
            logger.info(f"✅ Validation completed in {validation_time:.2f}s: Valid={is_valid}, TR3={tr3_compliance}, Issues={len(issues)}")
            
            return ValidationResult(
                is_valid=is_valid,
                issues=issues,
                segments_validated=len(parsed_edi.segments),
                validation_time=validation_time,
                tr3_compliance=tr3_compliance,
                suggested_improvements=suggestions
            )
            
        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return ValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    code="VAL001",
                    message=f"Validation process failed: {str(e)}"
                )],
                segments_validated=0,
                validation_time=0.0,
                tr3_compliance=False,
                suggested_improvements=["Fix validation process errors"]
            )
    
    def _validate_structure(self, parsed_edi: ParsedEDI) -> List[ValidationIssue]:
        """Validate overall EDI structure."""
        issues = []
        
        try:
            segments = parsed_edi.segments
            
            # Check for required envelope segments
            has_isa = any(seg.segment_id == 'ISA' for seg in segments)
            has_gs = any(seg.segment_id == 'GS' for seg in segments)
            has_st = any(seg.segment_id == 'ST' for seg in segments)
            has_se = any(seg.segment_id == 'SE' for seg in segments)
            has_ge = any(seg.segment_id == 'GE' for seg in segments)
            has_iea = any(seg.segment_id == 'IEA' for seg in segments)
            
            if not has_isa:
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    code="STR001",
                    message="Missing ISA (Interchange Header) segment",
                    suggested_fix="Add ISA segment at the beginning of the file"
                ))
            
            if not has_gs:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code="STR002",
                    message="Missing GS (Functional Group Header) segment",
                    suggested_fix="Add GS segment after ISA segment"
                ))
            
            if not has_st:
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    code="STR003",
                    message="Missing ST (Transaction Set Header) segment",
                    suggested_fix="Add ST segment to start transaction set"
                ))
            
            # Check segment count
            if len(segments) < 5:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code="STR004",
                    message=f"Very few segments detected: {len(segments)}",
                    suggested_fix="Verify file completeness and parsing accuracy"
                ))
            
            # Check for X12 278 specific segments
            has_bht = any(seg.segment_id == 'BHT' for seg in segments)
            if not has_bht:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    code="STR005",
                    message="Missing BHT (Beginning of Hierarchical Transaction) segment",
                    suggested_fix="Add BHT segment after ST segment for X12 278"
                ))
            
        except Exception as e:
            issues.append(ValidationIssue(
                level=ValidationLevel.CRITICAL,
                code="STR999",
                message=f"Structure validation error: {str(e)}"
            ))
        
        return issues
    
    def _validate_segments(self, parsed_edi: ParsedEDI) -> List[ValidationIssue]:
        """Validate individual segments."""
        issues = []
        
        try:
            for segment in parsed_edi.segments:
                # Check segment ID format
                if not segment.segment_id or len(segment.segment_id) < 2:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="SEG001",
                        message=f"Invalid segment ID: '{segment.segment_id}'",
                        segment=segment.segment_id,
                        line_number=segment.position
                    ))
                
                # Check for minimum elements based on segment type
                min_elements = {
                    'ISA': 16,
                    'GS': 8,
                    'ST': 2,
                    'BHT': 4,
                    'HL': 3,
                    'NM1': 3,
                    'SE': 2,
                    'GE': 2,
                    'IEA': 2
                }
                
                min_required = min_elements.get(segment.segment_id, 0)
                if min_required > 0 and len(segment.elements) < min_required:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        code="SEG002",
                        message=f"Segment {segment.segment_id} has {len(segment.elements)} elements, minimum {min_required} required",
                        segment=segment.segment_id,
                        line_number=segment.position,
                        suggested_fix=f"Add missing elements to {segment.segment_id} segment"
                    ))
        
        except Exception as e:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="SEG999",
                message=f"Segment validation error: {str(e)}"
            ))
        
        return issues
    
    def _validate_tr3_compliance(self, parsed_edi: ParsedEDI) -> List[ValidationIssue]:
        """Validate TR3 implementation guide compliance for X12 278."""
        issues = []
        
        try:
            segments = parsed_edi.segments
            
            # Check for required X12 278 transaction structure
            st_segments = [seg for seg in segments if seg.segment_id == 'ST']
            
            for st_seg in st_segments:
                if len(st_seg.elements) >= 1:
                    transaction_type = st_seg.elements[0]
                    if transaction_type != '278':
                        issues.append(ValidationIssue(
                            level=ValidationLevel.ERROR,
                            code="TR3001",
                            message=f"Expected transaction type 278, found {transaction_type}",
                            segment='ST',
                            line_number=st_seg.position,
                            suggested_fix="Change ST01 to '278' for X12 278 transactions"
                        ))
            
            # Check for required hierarchical structure
            hl_segments = [seg for seg in segments if seg.segment_id == 'HL']
            
            if not hl_segments:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="TR3002",
                    message="Missing HL (Hierarchical Level) segments required for X12 278",
                    suggested_fix="Add HL segments to define hierarchical structure"
                ))
            else:
                # Validate HL level codes for 278
                valid_level_codes = ['20', '21', '22', '23']
                for hl_seg in hl_segments:
                    if len(hl_seg.elements) >= 3:
                        level_code = hl_seg.elements[2]
                        if level_code not in valid_level_codes:
                            issues.append(ValidationIssue(
                                level=ValidationLevel.WARNING,
                                code="TR3003",
                                message=f"Unusual HL level code: {level_code}",
                                segment='HL',
                                line_number=hl_seg.position,
                                suggested_fix=f"Verify HL03 level code. Expected: {', '.join(valid_level_codes)}"
                            ))
            
            # Check for required NM1 segments with proper qualifiers
            nm1_segments = [seg for seg in segments if seg.segment_id == 'NM1']
            required_qualifiers = ['PR', 'IL']  # Payer, Insured (minimum required)
            recommended_qualifiers = ['82', '1P']  # Rendering Provider, Physician (recommended)
            
            found_qualifiers = []
            for nm1_seg in nm1_segments:
                if len(nm1_seg.elements) >= 1:
                    qualifier = nm1_seg.elements[0]
                    found_qualifiers.append(qualifier)
            
            # Check required qualifiers (errors)
            for req_qual in required_qualifiers:
                if req_qual not in found_qualifiers:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="TR3004",
                        message=f"Missing required NM1 segment with qualifier '{req_qual}'",
                        suggested_fix=f"Add NM1 segment with qualifier '{req_qual}' for party identification"
                    ))
            
            # Check recommended qualifiers (warnings)
            for rec_qual in recommended_qualifiers:
                if rec_qual not in found_qualifiers:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.INFO,
                        code="TR3004B",
                        message=f"Consider adding NM1 segment with qualifier '{rec_qual}' for complete identification",
                        suggested_fix=f"Add NM1 segment with qualifier '{rec_qual}' for enhanced compliance"
                    ))
            
            # Check version compliance
            if parsed_edi.header.version not in ['005010X279A1', '005010X217']:
                issues.append(ValidationIssue(
                    level=ValidationLevel.INFO,
                    code="TR3005",
                    message=f"Version {parsed_edi.header.version} may not be current TR3 compliant version",
                    suggested_fix="Consider updating to 005010X279A1 for latest TR3 compliance"
                ))
        
        except Exception as e:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="TR3999",
                message=f"TR3 validation error: {str(e)}"
            ))
        
        return issues
    
    def _generate_suggestions(self, issues: List[ValidationIssue]) -> List[str]:
        """Generate improvement suggestions based on validation issues."""
        suggestions = []
        
        try:
            # Count issues by level
            critical_count = len([i for i in issues if i.level == ValidationLevel.CRITICAL])
            error_count = len([i for i in issues if i.level == ValidationLevel.ERROR])
            warning_count = len([i for i in issues if i.level == ValidationLevel.WARNING])
            
            # Priority-based suggestions
            if critical_count > 0:
                suggestions.append(f"URGENT: Fix {critical_count} critical issue(s) that prevent processing")
                suggestions.append("Focus on structural integrity and required segments first")
            
            if error_count > 0:
                suggestions.append(f"Address {error_count} error(s) for full compliance")
                suggestions.append("Review segment element counts and data formats")
            
            if warning_count > 0:
                suggestions.append(f"Consider resolving {warning_count} warning(s) for optimal compliance")
            
            # Specific suggestions based on common issues
            issue_codes = [issue.code for issue in issues]
            
            if 'STR001' in issue_codes or 'STR003' in issue_codes:
                suggestions.append("Verify file contains complete EDI envelope structure")
            
            if 'TR3002' in issue_codes:
                suggestions.append("Add hierarchical structure with HL segments for X12 278 compliance")
            
            if 'SEG002' in issue_codes:
                suggestions.append("Check segment element requirements against X12 278 TR3 guide")
            
            # Add general suggestions if no specific issues
            if not issues:
                suggestions.append("Document appears to be well-formed and compliant")
                suggestions.append("Consider periodic validation against updated TR3 specifications")
            
        except Exception as e:
            logger.warning(f"Error generating suggestions: {e}")
            suggestions.append("Review validation results and address identified issues")
        
        return suggestions[:10]  # Limit to top 10 suggestions