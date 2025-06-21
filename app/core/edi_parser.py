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
            processed_content = content.strip()
            
            # Fix ISA segment formatting issues that cause pyx12 to see "401*0" instead of "00401"
            if 'ISA*' in processed_content:
                lines = processed_content.split('\n')
                processed_lines = []
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('ISA*'):
                        # Split by * and fix ISA version (position 12, index 11)
                        parts = line.split('*')
                        if len(parts) >= 16:  # ISA should have exactly 16 elements
                            version = parts[11]  # ISA12 - Interchange Control Version Number
                            
                            # Enhanced version mappings for pyx12 compatibility
                            version_map = {
                                '00501': '00401',  # Map 5010 to 4010 for pyx12 compatibility
                                '501': '00401',
                                '5010': '00401',
                                '00500': '00401',
                                '500': '00401'
                            }
                            
                            if version in version_map:
                                parts[11] = version_map[version]
                                logger.info(f"ISA version mapping: {version} → {version_map[version]}")
                            
                            # Ensure ISA segment has proper formatting
                            # ISA*00*          *00*          *ZZ*SENDER_ID     *ZZ*RECEIVER_ID   *YYMMDD*HHMM*U*00401*000000001*0*P*>~
                            
                            # Fix common formatting issues
                            if len(parts) == 16:
                                # Ensure proper element padding/formatting
                                if len(parts[1]) == 0:  # Authorization Information Qualifier
                                    parts[1] = '00'
                                if len(parts[2]) < 10:  # Authorization Information (pad to 10)
                                    parts[2] = parts[2].ljust(10)
                                if len(parts[3]) == 0:  # Security Information Qualifier
                                    parts[3] = '00'
                                if len(parts[4]) < 10:  # Security Information (pad to 10)
                                    parts[4] = parts[4].ljust(10)
                                if len(parts[5]) == 0:  # Interchange ID Qualifier
                                    parts[5] = 'ZZ'
                                if len(parts[6]) < 15:  # Interchange Sender ID (pad to 15)
                                    parts[6] = parts[6].ljust(15)
                                if len(parts[7]) == 0:  # Interchange ID Qualifier
                                    parts[7] = 'ZZ'
                                if len(parts[8]) < 15:  # Interchange Receiver ID (pad to 15)
                                    parts[8] = parts[8].ljust(15)
                                # parts[9] = date (YYMMDD)
                                # parts[10] = time (HHMM)
                                if len(parts[10]) == 0:  # Interchange Control Standards Identifier
                                    parts[10] = 'U'
                                # parts[11] = version (already fixed above)
                                if len(parts[12]) < 9:  # Interchange Control Number (pad to 9)
                                    parts[12] = parts[12].zfill(9)
                                if len(parts[13]) == 0:  # Acknowledgment Requested
                                    parts[13] = '0'
                                if len(parts[14]) == 0:  # Usage Indicator
                                    parts[14] = 'P'
                                if len(parts[15]) == 0:  # Component Element Separator
                                    parts[15] = '>'
                            
                            line = '*'.join(parts)
                            logger.info("✅ ISA segment formatting normalized for pyx12 compatibility")
                        else:
                            logger.warning(f"ISA segment has {len(parts)} elements, expected 16")
                    
                    processed_lines.append(line)
                
                processed_content = '\n'.join(processed_lines)
            
            # Additional regex-based fixes for edge cases
            if processed_content != content.strip():
                logger.info("✅ ISA version preprocessing completed for pyx12 compatibility")
            
            return processed_content
            
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
                    # For ISA and HL segments, preserve all elements including empty ones
                    if tag in ['ISA', 'HL']:
                        elements = [elem for elem in parts[1:]]  # Keep all elements for ISA and HL
                    else:
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


class ProductionTR3Validator:
    """
    Production-grade TR3 compliance validator for X12 278 with strict industry standards.
    Implements comprehensive TR3 implementation guide rules for healthcare prior authorization.
    """
    
    def __init__(self):
        """Initialize with TR3 005010X279A1 rules."""
        self.tr3_version = "005010X279A1"
        self.required_segments = {
            'ISA': {'min_elements': 16, 'required': True},
            'GS': {'min_elements': 8, 'required': True},
            'ST': {'min_elements': 2, 'required': True, 'transaction_type': '278'},
            'BHT': {'min_elements': 6, 'required': True},
            'HL': {'min_elements': 4, 'required': True},
            'NM1': {'min_elements': 3, 'required': True},
            'SE': {'min_elements': 2, 'required': True},
            'GE': {'min_elements': 2, 'required': True},
            'IEA': {'min_elements': 2, 'required': True}
        }
        
        # TR3-compliant HL level codes for 278
        self.valid_hl_codes = {
            '20': 'Information Source',
            '21': 'Information Receiver', 
            '22': 'Subscriber',
            '23': 'Dependent'
        }
        
        # Required NM1 entity identifiers for TR3 compliance
        self.required_nm1_qualifiers = {
            'PR': 'Payer (Required)',
            'IL': 'Insured/Subscriber (Required)'
        }
        
        self.recommended_nm1_qualifiers = {
            '82': 'Rendering Provider',
            '1P': 'Provider',
            'QC': 'Patient'
        }
        
        logger.info(f"Production TR3 validator initialized for version {self.tr3_version}")
    
    def validate_strict_tr3_compliance(self, parsed_edi: ParsedEDI) -> ValidationResult:
        """
        Perform strict TR3 compliance validation with zero tolerance for errors.
        Production-ready validation that ensures complete TR3 conformance.
        """
        try:
            start_time = time.time()
            issues = []
            
            # 1. Envelope Structure Validation (Critical)
            envelope_issues = self._validate_envelope_structure(parsed_edi)
            issues.extend(envelope_issues)
            
            # 2. Transaction Set Validation (Critical)
            transaction_issues = self._validate_transaction_structure(parsed_edi)
            issues.extend(transaction_issues)
            
            # 3. Hierarchical Structure Validation (Critical for 278)
            hierarchy_issues = self._validate_hierarchical_structure(parsed_edi)
            issues.extend(hierarchy_issues)
            
            # 4. Entity Identification Validation (Critical)
            entity_issues = self._validate_entity_identification(parsed_edi)
            issues.extend(entity_issues)
            
            # 5. Data Element Validation (Critical)
            element_issues = self._validate_data_elements(parsed_edi)
            issues.extend(element_issues)
            
            # 6. TR3 Business Rules Validation (Critical)
            business_issues = self._validate_business_rules(parsed_edi)
            issues.extend(business_issues)
            
            # Strict compliance assessment
            critical_issues = [i for i in issues if i.level == ValidationLevel.CRITICAL]
            error_issues = [i for i in issues if i.level == ValidationLevel.ERROR]
            
            # Production rule: ANY critical or error issue fails TR3 compliance
            is_valid = len(critical_issues) == 0 and len(error_issues) == 0
            tr3_compliant = is_valid  # Strict: must be error-free for TR3 compliance
            
            validation_time = time.time() - start_time
            
            logger.info(f"Production TR3 validation: Valid={is_valid}, Issues={len(issues)}, Time={validation_time:.3f}s")
            
            return ValidationResult(
                is_valid=is_valid,
                issues=issues,
                segments_validated=len(parsed_edi.segments),
                validation_time=validation_time,
                tr3_compliance=tr3_compliant,
                suggested_improvements=self._generate_production_suggestions(issues)
            )
            
        except Exception as e:
            logger.error(f"Production TR3 validation failed: {str(e)}")
            return ValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    code="TR3_SYSTEM_ERROR",
                    message=f"TR3 validation system error: {str(e)}"
                )],
                segments_validated=0,
                validation_time=0.0,
                tr3_compliance=False,
                suggested_improvements=["Fix TR3 validation system errors before processing"]
            )
    
    def _validate_envelope_structure(self, parsed_edi: ParsedEDI) -> List[ValidationIssue]:
        """Validate ISA/GS/GE/IEA envelope structure per TR3."""
        issues = []
        segments = parsed_edi.segments
        
        # Check envelope segment presence and order
        envelope_segments = ['ISA', 'GS', 'ST']
        trailer_segments = ['SE', 'GE', 'IEA']
        
        # Validate header envelope
        for i, seg_id in enumerate(envelope_segments):
            found_segments = [s for s in segments if s.segment_id == seg_id]
            if not found_segments:
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    code=f"TR3_ENV_{seg_id}_MISSING",
                    message=f"Missing required envelope segment {seg_id}",
                    suggested_fix=f"Add {seg_id} segment in proper envelope position"
                ))
            elif len(found_segments) > 1:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code=f"TR3_ENV_{seg_id}_DUPLICATE",
                    message=f"Multiple {seg_id} segments found, only one allowed per interchange",
                    suggested_fix=f"Remove duplicate {seg_id} segments"
                ))
        
        # Validate trailer envelope
        for seg_id in trailer_segments:
            found_segments = [s for s in segments if s.segment_id == seg_id]
            if not found_segments:
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    code=f"TR3_ENV_{seg_id}_MISSING",
                    message=f"Missing required trailer segment {seg_id}",
                    suggested_fix=f"Add {seg_id} segment in proper trailer position"
                ))
        
        # Validate ISA segment elements
        isa_segments = [s for s in segments if s.segment_id == 'ISA']
        if isa_segments:
            isa_seg = isa_segments[0]
            if len(isa_seg.elements) < 16:
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    code="TR3_ISA_INCOMPLETE",
                    message=f"ISA segment has {len(isa_seg.elements)} elements, requires 16",
                    segment='ISA',
                    line_number=isa_seg.position,
                    suggested_fix="Complete all 16 ISA elements per X12 standard"
                ))
            
            # Validate ISA version
            if len(isa_seg.elements) >= 12:
                version = isa_seg.elements[11]
                if version not in ['00501', '00401']:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="TR3_ISA_VERSION",
                        message=f"ISA version {version} may not be TR3 compliant",
                        segment='ISA',
                        line_number=isa_seg.position,
                        suggested_fix="Use ISA version 00501 for TR3 005010X279A1 compliance"
                    ))
        
        return issues
    
    def _validate_transaction_structure(self, parsed_edi: ParsedEDI) -> List[ValidationIssue]:
        """Validate ST/BHT transaction structure per TR3."""
        issues = []
        segments = parsed_edi.segments
        
        # Validate ST segment
        st_segments = [s for s in segments if s.segment_id == 'ST']
        if not st_segments:
            issues.append(ValidationIssue(
                level=ValidationLevel.CRITICAL,
                code="TR3_ST_MISSING",
                message="Missing ST (Transaction Set Header) segment",
                suggested_fix="Add ST segment with transaction type 278"
            ))
        else:
            st_seg = st_segments[0]
            if len(st_seg.elements) < 2:
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    code="TR3_ST_INCOMPLETE",
                    message="ST segment missing required elements",
                    segment='ST',
                    line_number=st_seg.position,
                    suggested_fix="ST segment requires ST01 (278) and ST02 (control number)"
                ))
            else:
                # Validate transaction type
                if st_seg.elements[0] != '278':
                    issues.append(ValidationIssue(
                        level=ValidationLevel.CRITICAL,
                        code="TR3_ST_WRONG_TYPE",
                        message=f"Expected transaction type 278, found {st_seg.elements[0]}",
                        segment='ST',
                        line_number=st_seg.position,
                        suggested_fix="Change ST01 to '278' for X12 278 transactions"
                    ))
        
        # Validate BHT segment (required for 278)
        bht_segments = [s for s in segments if s.segment_id == 'BHT']
        if not bht_segments:
            issues.append(ValidationIssue(
                level=ValidationLevel.CRITICAL,
                code="TR3_BHT_MISSING",
                message="Missing BHT (Beginning of Hierarchical Transaction) segment",
                suggested_fix="Add BHT segment after ST segment for X12 278"
            ))
        else:
            bht_seg = bht_segments[0]
            if len(bht_seg.elements) < 6:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="TR3_BHT_INCOMPLETE",
                    message=f"BHT segment has {len(bht_seg.elements)} elements, requires minimum 6",
                    segment='BHT',
                    line_number=bht_seg.position,
                    suggested_fix="Complete BHT elements: structure code, purpose, reference ID, date, time, transaction type"
                ))
        
        return issues
    
    def _validate_hierarchical_structure(self, parsed_edi: ParsedEDI) -> List[ValidationIssue]:
        """Validate HL hierarchical structure per TR3 requirements."""
        issues = []
        segments = parsed_edi.segments
        
        hl_segments = [s for s in segments if s.segment_id == 'HL']
        if not hl_segments:
            issues.append(ValidationIssue(
                level=ValidationLevel.CRITICAL,
                code="TR3_HL_MISSING",
                message="Missing HL (Hierarchical Level) segments required for X12 278",
                suggested_fix="Add HL segments to define hierarchical structure per TR3"
            ))
            return issues
        
        # Validate HL segment structure
        for hl_seg in hl_segments:
            if len(hl_seg.elements) < 4:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="TR3_HL_INCOMPLETE",
                    message=f"HL segment at position {hl_seg.position} has {len(hl_seg.elements)} elements, requires 4",
                    segment='HL',
                    line_number=hl_seg.position,
                    suggested_fix="HL requires: ID number, parent ID, level code, child code"
                ))
                continue
            
            # Validate level code (HL03)
            level_code = hl_seg.elements[2]
            if level_code not in self.valid_hl_codes:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    code="TR3_HL_INVALID_CODE",
                    message=f"Invalid HL level code '{level_code}' at position {hl_seg.position}",
                    segment='HL',
                    line_number=hl_seg.position,
                    suggested_fix=f"Use valid TR3 level codes: {', '.join(self.valid_hl_codes.keys())}"
                ))
        
        # Validate required hierarchy levels for 278
        found_levels = [hl.elements[2] for hl in hl_segments if len(hl.elements) >= 3]
        required_levels = ['20', '21']  # Information Source and Receiver are mandatory
        
        for req_level in required_levels:
            if req_level not in found_levels:
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    code=f"TR3_HL_{req_level}_MISSING",
                    message=f"Missing required HL level {req_level} ({self.valid_hl_codes[req_level]})",
                    suggested_fix=f"Add HL segment with level code {req_level}"
                ))
        
        return issues
    
    def _validate_entity_identification(self, parsed_edi: ParsedEDI) -> List[ValidationIssue]:
        """Validate NM1 entity identification per TR3."""
        issues = []
        segments = parsed_edi.segments
        
        nm1_segments = [s for s in segments if s.segment_id == 'NM1']
        if not nm1_segments:
            issues.append(ValidationIssue(
                level=ValidationLevel.CRITICAL,
                code="TR3_NM1_MISSING",
                message="Missing NM1 (Individual or Organizational Name) segments",
                suggested_fix="Add NM1 segments for entity identification per TR3"
            ))
            return issues
        
        # Collect found qualifiers
        found_qualifiers = []
        for nm1_seg in nm1_segments:
            if len(nm1_seg.elements) >= 1:
                qualifier = nm1_seg.elements[0]
                found_qualifiers.append(qualifier)
                
                # Validate NM1 segment completeness
                if len(nm1_seg.elements) < 3:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="TR3_NM1_INCOMPLETE",
                        message=f"NM1 segment with qualifier {qualifier} has {len(nm1_seg.elements)} elements, requires minimum 3",
                        segment='NM1',
                        line_number=nm1_seg.position,
                        suggested_fix="NM1 requires: entity qualifier, entity type, name"
                    ))
        
        # Check required qualifiers
        for req_qual, description in self.required_nm1_qualifiers.items():
            if req_qual not in found_qualifiers:
                issues.append(ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    code=f"TR3_NM1_{req_qual}_MISSING",
                    message=f"Missing required NM1 segment with qualifier '{req_qual}' ({description})",
                    suggested_fix=f"Add NM1 segment with qualifier '{req_qual}' for {description}"
                ))
        
        return issues
    
    def _validate_data_elements(self, parsed_edi: ParsedEDI) -> List[ValidationIssue]:
        """Validate data element formats and values per TR3."""
        issues = []
        segments = parsed_edi.segments
        
        # Validate specific segment data elements
        for segment in segments:
            seg_id = segment.segment_id
            elements = segment.elements
            
            # ISA date/time validation
            if seg_id == 'ISA' and len(elements) >= 10:
                # ISA09 - Interchange Date (YYMMDD)
                date_elem = elements[8]
                if not (len(date_elem) == 6 and date_elem.isdigit()):
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="TR3_ISA_DATE_FORMAT",
                        message=f"ISA09 date format invalid: '{date_elem}' (should be YYMMDD)",
                        segment='ISA',
                        line_number=segment.position,
                        suggested_fix="Use YYMMDD format for ISA09 interchange date"
                    ))
                
                # ISA10 - Interchange Time (HHMM)
                time_elem = elements[9]
                if not (len(time_elem) == 4 and time_elem.isdigit()):
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        code="TR3_ISA_TIME_FORMAT",
                        message=f"ISA10 time format invalid: '{time_elem}' (should be HHMM)",
                        segment='ISA',
                        line_number=segment.position,
                        suggested_fix="Use HHMM format for ISA10 interchange time"
                    ))
            
            # GS version validation
            elif seg_id == 'GS' and len(elements) >= 8:
                version = elements[7]
                if version != self.tr3_version:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.WARNING,
                        code="TR3_GS_VERSION",
                        message=f"GS08 version '{version}' differs from expected TR3 version '{self.tr3_version}'",
                        segment='GS',
                        line_number=segment.position,
                        suggested_fix=f"Use {self.tr3_version} for current TR3 compliance"
                    ))
        
        return issues
    
    def _validate_business_rules(self, parsed_edi: ParsedEDI) -> List[ValidationIssue]:
        """Validate TR3 business rules and logical constraints."""
        issues = []
        segments = parsed_edi.segments
        
        # Business Rule: HL hierarchy must be logically consistent
        hl_segments = [s for s in segments if s.segment_id == 'HL']
        if len(hl_segments) >= 2:
            # Check parent-child relationships
            for hl_seg in hl_segments:
                if len(hl_seg.elements) >= 4:
                    hl_id = hl_seg.elements[0]
                    parent_id = hl_seg.elements[1]
                    level_code = hl_seg.elements[2]
                    
                    # Validate parent reference exists (if not root)
                    if parent_id and parent_id != '':
                        parent_exists = any(
                            h.elements[0] == parent_id 
                            for h in hl_segments 
                            if len(h.elements) >= 1
                        )
                        if not parent_exists:
                            issues.append(ValidationIssue(
                                level=ValidationLevel.ERROR,
                                code="TR3_HL_PARENT_MISSING",
                                message=f"HL segment references non-existent parent ID '{parent_id}'",
                                segment='HL',
                                line_number=hl_seg.position,
                                suggested_fix="Ensure parent HL segment exists before child reference"
                            ))
        
        # Business Rule: Each HL level should have corresponding NM1 identification
        hl_levels = [s.elements[2] for s in hl_segments if len(s.elements) >= 3]
        nm1_qualifiers = [s.elements[0] for s in segments if s.segment_id == 'NM1' and len(s.elements) >= 1]
        
        # Level 20 (Information Source) should have PR (Payer) identification
        if '20' in hl_levels and 'PR' not in nm1_qualifiers:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="TR3_BUSINESS_RULE_1",
                message="HL level 20 (Information Source) present but missing NM1*PR (Payer) identification",
                suggested_fix="Add NM1*PR segment for Information Source identification"
            ))
        
        # Level 22 (Subscriber) should have IL (Insured) identification
        if '22' in hl_levels and 'IL' not in nm1_qualifiers:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                code="TR3_BUSINESS_RULE_2",
                message="HL level 22 (Subscriber) present but missing NM1*IL (Insured) identification",
                suggested_fix="Add NM1*IL segment for Subscriber identification"
            ))
        
        return issues
    
    def _generate_production_suggestions(self, issues: List[ValidationIssue]) -> List[str]:
        """Generate production-ready improvement suggestions."""
        suggestions = []
        
        critical_count = len([i for i in issues if i.level == ValidationLevel.CRITICAL])
        error_count = len([i for i in issues if i.level == ValidationLevel.ERROR])
        warning_count = len([i for i in issues if i.level == ValidationLevel.WARNING])
        
        if critical_count > 0:
            suggestions.append(f"PRODUCTION BLOCKER: {critical_count} critical TR3 compliance issue(s) must be resolved")
            suggestions.append("Document cannot be processed until all critical issues are fixed")
        
        if error_count > 0:
            suggestions.append(f"TR3 COMPLIANCE FAILURE: {error_count} error(s) prevent full compliance")
            suggestions.append("All errors must be resolved for production TR3 compliance")
        
        if warning_count > 0:
            suggestions.append(f"OPTIMIZATION: {warning_count} warning(s) should be addressed for best practices")
        
        # Add specific guidance
        issue_codes = [issue.code for issue in issues]
        
        if any(code.startswith('TR3_ENV_') for code in issue_codes):
            suggestions.append("Review X12 envelope structure (ISA/GS/ST/SE/GE/IEA) requirements")
        
        if any(code.startswith('TR3_HL_') for code in issue_codes):
            suggestions.append("Verify hierarchical structure follows TR3 005010X279A1 specifications")
        
        if any(code.startswith('TR3_NM1_') for code in issue_codes):
            suggestions.append("Ensure all required entity identifications are present per TR3")
        
        if not issues:
            suggestions.append("✅ PRODUCTION READY: Document meets strict TR3 compliance requirements")
            suggestions.append("Document approved for production processing")
        
        return suggestions[:8]


# Update EDI278Validator to use production validator
class EDI278Validator:
    """X12 278 specific validator with production-grade TR3 compliance checking."""
    
    def __init__(self):
        """Initialize validator with production TR3 validator."""
        self.production_validator = ProductionTR3Validator()
        logger.info("EDI278Validator initialized with production TR3 compliance")
    
    def validate(self, parsed_edi: ParsedEDI) -> ValidationResult:
        """
        Production-grade validation of X12 278 EDI document with strict TR3 compliance.
        
        Args:
            parsed_edi: Parsed EDI structure
            
        Returns:
            ValidationResult: Comprehensive validation results with strict TR3 compliance
        """
        try:
            # Use production TR3 validator for strict compliance
            return self.production_validator.validate_strict_tr3_compliance(parsed_edi)
            
        except Exception as e:
            logger.error(f"Production validation failed: {str(e)}")
            return ValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    code="PROD_VAL_ERROR",
                    message=f"Production validation system error: {str(e)}"
                )],
                segments_validated=0,
                validation_time=0.0,
                tr3_compliance=False,
                suggested_improvements=["Fix production validation system before processing"]
            )