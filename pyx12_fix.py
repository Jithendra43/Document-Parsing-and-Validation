"""
Compatibility fixes for pyx12 with modern Python versions.
This module provides fallback mechanisms when pyx12 fails.
"""

import re
import sys
from typing import List, Dict, Any, Optional

class ModernEDIParser:
    """
    Modern EDI parser that handles pyx12 compatibility issues.
    Provides enhanced parsing for Python 3.10+ environments.
    """
    
    def __init__(self):
        self.segment_terminator = '~'
        self.element_separator = '*'
        self.component_separator = '^'
        
    def parse_edi_content(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse EDI content with modern Python compatibility.
        
        Args:
            content: Raw EDI content string
            
        Returns:
            List of parsed segments
        """
        segments = []
        
        # Clean and normalize content
        content = content.strip()
        
        # Split into segments
        raw_segments = content.split(self.segment_terminator)
        
        for i, raw_segment in enumerate(raw_segments):
            if not raw_segment.strip():
                continue
                
            # Parse segment
            segment = self._parse_segment(raw_segment.strip(), i + 1)
            if segment:
                segments.append(segment)
        
        return segments
    
    def _parse_segment(self, segment_text: str, position: int) -> Optional[Dict[str, Any]]:
        """Parse individual segment."""
        if not segment_text or len(segment_text) < 2:
            return None
            
        parts = segment_text.split(self.element_separator)
        if not parts:
            return None
            
        segment_id = parts[0].strip()
        elements = [elem.strip() for elem in parts[1:] if elem.strip()]
        
        return {
            'tag': segment_id,
            'elements': elements,
            'raw': segment_text,
            'position': position
        }
    
    def validate_isa_segment(self, isa_data: List[str]) -> bool:
        """
        Validate ISA segment with flexible version handling.
        Fixes the "unknown version" error in pyx12.
        """
        if len(isa_data) < 16:
            return False
            
        # More flexible version validation
        version = isa_data[11] if len(isa_data) > 11 else "00501"
        
        # Accept common X12 versions
        valid_versions = [
            "00501", "00401", "00402", "00403", "00404", "00405",
            "005010", "004010", "004020", "004030", "004040", "004050"
        ]
        
        # Normalize version format
        normalized_version = version.strip().zfill(5)
        
        return any(normalized_version.startswith(v[:3]) for v in valid_versions)


def fix_pyx12_version_error(edi_content: str) -> str:
    """
    Fix common pyx12 version errors by normalizing ISA segments.
    
    Args:
        edi_content: Original EDI content
        
    Returns:
        Fixed EDI content with normalized ISA segment
    """
    # Pattern to match ISA segment
    isa_pattern = r'ISA\*([^~]+)~'
    
    match = re.search(isa_pattern, edi_content)
    if not match:
        return edi_content
    
    isa_elements = match.group(1).split('*')
    
    if len(isa_elements) >= 12:
        # Fix version number (element 12, index 11)
        version = isa_elements[11]
        
        # Common version fixes
        if version in ['501', '5010']:
            isa_elements[11] = '00501'
        elif version in ['401', '4010']:
            isa_elements[11] = '00401'
        elif len(version) == 3:
            isa_elements[11] = '00' + version
        elif len(version) == 4:
            isa_elements[11] = '0' + version
            
        # Reconstruct ISA segment
        fixed_isa = 'ISA*' + '*'.join(isa_elements) + '~'
        
        # Replace in original content
        return re.sub(isa_pattern, fixed_isa, edi_content)
    
    return edi_content


def get_python_version_info():
    """Get Python version compatibility info."""
    version = sys.version_info
    
    compatibility = {
        'version': f"{version.major}.{version.minor}.{version.micro}",
        'pyx12_compatible': version.major == 3 and 7 <= version.minor <= 9,
        'recommended_action': None
    }
    
    if version.major == 3:
        if version.minor >= 11:
            compatibility['recommended_action'] = "Consider downgrading to Python 3.9 for optimal pyx12 compatibility"
        elif version.minor == 10:
            compatibility['recommended_action'] = "Good compatibility, may need some fixes"
        elif 7 <= version.minor <= 9:
            compatibility['recommended_action'] = "Excellent compatibility with pyx12"
        else:
            compatibility['recommended_action'] = "Upgrade to Python 3.9 for best results"
    
    return compatibility


if __name__ == "__main__":
    info = get_python_version_info()
    print(f"Python Version: {info['version']}")
    print(f"pyx12 Compatible: {info['pyx12_compatible']}")
    if info['recommended_action']:
        print(f"Recommendation: {info['recommended_action']}") 