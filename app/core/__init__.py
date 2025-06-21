"""Core EDI processing modules with error handling."""

# Import core modules with error handling
from .models import *
from .logger import get_logger, configure_logging
from .edi_parser import EDI278Parser, EDI278Validator

# Try to import FHIR mapper with fallback
try:
    from .fhir_mapper import X12To278FHIRMapper, FHIRToX12Mapper, ProductionFHIRMapper
except ImportError as e:
    # Create fallback FHIR mappers
    import warnings
    warnings.warn(f"FHIR mapper not available: {e}")
    
    class FallbackFHIRMapper:
        def __init__(self):
            self.logger = get_logger(self.__class__.__name__)
            self.logger.warning("Using fallback FHIR mapper - full FHIR functionality not available")
        
        def map_to_fhir(self, edi_data):
            from .models import FHIRMapping, FHIRResource
            return FHIRMapping(
                resources=[
                    FHIRResource(
                        resource_type="OperationOutcome",
                        data={
                            "resourceType": "OperationOutcome",
                            "issue": [{
                                "severity": "warning",
                                "code": "not-supported",
                                "details": {"text": "FHIR library not available - using fallback"}
                            }]
                        }
                    )
                ]
            )
    
    # Use fallback classes
    X12To278FHIRMapper = FallbackFHIRMapper
    FHIRToX12Mapper = FallbackFHIRMapper
    ProductionFHIRMapper = FallbackFHIRMapper

__all__ = [
    'EDI278Parser',
    'EDI278Validator', 
    'X12To278FHIRMapper',
    'FHIRToX12Mapper',
    'ProductionFHIRMapper',
    'get_logger',
    'configure_logging'
] 