"""FHIR mapping for X12 278 EDI transactions following Da Vinci PAS TR3 implementation guide."""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from fhir.resources.patient import Patient
from fhir.resources.practitioner import Practitioner
from fhir.resources.organization import Organization
from fhir.resources.coverageeligibilityrequest import CoverageEligibilityRequest
from fhir.resources.coverageeligibilityresponse import CoverageEligibilityResponse
from fhir.resources.coverage import Coverage
from fhir.resources.humanname import HumanName
from fhir.resources.address import Address
from fhir.resources.contactpoint import ContactPoint
from fhir.resources.identifier import Identifier
from fhir.resources.reference import Reference
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.bundle import Bundle
from fhir.resources.bundle import BundleEntry
from fhir.resources.period import Period
from fhir.resources.meta import Meta
from fhir.resources.money import Money
from fhir.resources.quantity import Quantity
from fhir.resources.extension import Extension

from app.core.models import (
    EDI278ParsedData, 
    FHIRMappingResult, 
    ValidationResult,
    EDI278Segment
)
from app.core.logger import get_logger

logger = get_logger(__name__)


class FHIRMappingError(Exception):
    """Exception raised for FHIR mapping errors."""
    pass


class X12To278FHIRMapper:
    """
    Maps X12 278 EDI data to FHIR CoverageEligibilityRequest resources 
    following Da Vinci PAS Implementation Guide TR3 compliance.
    
    This mapper converts X12 278 prior authorization requests to proper
    FHIR CoverageEligibilityRequest bundles as per healthcare standards.
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        
    def map_to_fhir(self, edi_data) -> FHIRMappingResult:
        """
        Map parsed X12 278 EDI data to FHIR CoverageEligibilityRequest bundle.
        
        Args:
            edi_data: Parsed X12 278 EDI data
            
        Returns:
            FHIRMappingResult containing the FHIR bundle and metadata
        """
        try:
            self.logger.info("Starting X12 278 to FHIR CoverageEligibilityRequest mapping")
            
            # Create main bundle
            bundle = Bundle(
                id=str(uuid.uuid4()),
                type="collection",
                timestamp=datetime.utcnow().isoformat(),
                identifier=Identifier(
                    system="urn:ietf:rfc:3986",
                    value=f"urn:uuid:{uuid.uuid4()}"
                )
            )
            
            # Map core resources
            patient = self._map_patient(edi_data)
            organization = self._map_organization(edi_data)
            practitioner = self._map_practitioner(edi_data)
            coverage = self._map_coverage(edi_data, patient, organization)
            
            # Create CoverageEligibilityRequest (main resource for 278)
            coverage_eligibility_request = self._map_coverage_eligibility_request(
                edi_data, patient, coverage, organization, practitioner
            )
            
            # Add all resources to bundle
            bundle.entry = [
                BundleEntry(resource=coverage_eligibility_request),
                BundleEntry(resource=patient),
                BundleEntry(resource=coverage),
                BundleEntry(resource=organization),
                BundleEntry(resource=practitioner)
            ]
            
            # Convert to dict for JSON serialization
            fhir_json = bundle.dict()
            
            # Create FHIRMapping object for compatibility
            from .models import FHIRMapping, FHIRResource
            
            # Extract resources from bundle
            fhir_resources = []
            for entry in bundle.entry:
                resource = entry.resource
                resource_dict = resource.dict()
                fhir_resources.append(FHIRResource(
                    resource_type=resource_dict.get('resourceType', resource.__class__.__name__),
                    id=resource.id,
                    data=resource_dict
                ))
            
            fhir_mapping = FHIRMapping(
                resources=fhir_resources,
                mapping_version="1.0",
                mapped_at=datetime.utcnow(),
                source_segments=[seg.segment_id for seg in edi_data.segments[:10]]  # First 10 segments
            )
            
            self.logger.info("Successfully mapped X12 278 to FHIR CoverageEligibilityRequest")
            
            return fhir_mapping
            
        except Exception as e:
            self.logger.error(f"FHIR mapping failed: {str(e)}")
            raise FHIRMappingError(f"Failed to map X12 278 to FHIR: {str(e)}")
    
    def _map_patient(self, edi_data) -> Patient:
        """Map X12 278 patient information to FHIR Patient resource."""
        try:
            # Extract patient data from 2000C/2010CA loops (subscriber/patient)
            patient_segment = self._find_segment(edi_data.segments, "NM1", qualifier="IL")
            demographic_segment = self._find_segment(edi_data.segments, "DMG")
            
            patient = Patient(
                id=str(uuid.uuid4()),
                meta=Meta(
                    profile=["http://hl7.org/fhir/us/davinci-pas/StructureDefinition/profile-beneficiary"]
                )
            )
            
            if patient_segment:
                # Parse NM1 segment for patient name
                name_parts = patient_segment.elements
                if len(name_parts) >= 4:
                    patient.name = [
                        HumanName(
                            family=name_parts[2] if len(name_parts) > 2 else "",
                            given=[name_parts[3]] if len(name_parts) > 3 else []
                        )
                    ]
                
                # Add identifier from NM1*IL segment
                if len(name_parts) >= 9:
                    patient.identifier = [
                        Identifier(
                            type=CodeableConcept(
                                coding=[
                                    Coding(
                                        system="http://terminology.hl7.org/CodeSystem/v2-0203",
                                        code="MB",
                                        display="Member Number"
                                    )
                                ]
                            ),
                            value=name_parts[8],
                            system="http://example.org/member-id"
                        )
                    ]
            
            # Parse demographic information
            if demographic_segment:
                demo_parts = demographic_segment.elements
                if len(demo_parts) >= 2:
                    # DOB in CCYYMMDD format
                    dob_str = demo_parts[1]
                    if len(dob_str) == 8:
                        patient.birthDate = f"{dob_str[:4]}-{dob_str[4:6]}-{dob_str[6:]}"
                
                if len(demo_parts) >= 3:
                    # Gender
                    gender_code = demo_parts[2]
                    gender_map = {"M": "male", "F": "female", "U": "unknown"}
                    patient.gender = gender_map.get(gender_code, "unknown")
            
            return patient
            
        except Exception as e:
            self.logger.error(f"Failed to map patient: {str(e)}")
            raise FHIRMappingError(f"Patient mapping failed: {str(e)}")
    
    def _map_coverage(self, edi_data, patient: Patient, organization: Organization) -> Coverage:
        """Map EDI data to FHIR Coverage resource."""
        try:
            logger.info("Mapping Coverage resource")
            
            # Find insurance segments - handle both dict and ParsedEDI object
            if hasattr(edi_data, 'segments'):
                segments = edi_data.segments
            elif isinstance(edi_data, dict) and 'segments' in edi_data:
                segments = edi_data['segments']
            else:
                segments = []
                
            nm1_segments = self._find_all_segments(segments, 'NM1')
            insurance_info = None
            
            for segment in nm1_segments:
                # Handle both dict and EDISegment objects
                if hasattr(segment, 'elements'):
                    elements = segment.elements
                elif isinstance(segment, dict):
                    elements = segment.get('elements', [])
                else:
                    continue
                    
                if len(elements) > 1:
                    entity_type = elements[1] if len(elements) > 1 else None
                    if entity_type == 'PR':  # Payer
                        insurance_info = {'elements': elements}
                        break
            
            if not insurance_info:
                logger.warning("No insurance information found, using default")
                insurance_info = {'elements': ['NM1', 'PR', '2', 'DEFAULT_INSURANCE']}
            
            # Create insurance organization reference using the actual organization ID
            insurance_org_ref = Reference(
                reference=f"Organization/{organization.id}",
                display=organization.name or "Insurance Company"
            )
            
            coverage = Coverage(
                id=str(uuid.uuid4()),
                meta=Meta(
                    profile=["http://hl7.org/fhir/us/davinci-pas/StructureDefinition/profile-coverage"]
                ),
                status="active",
                kind="insurance",  # Required field
                beneficiary=Reference(reference=f"Patient/{patient.id}"),
                insurer=insurance_org_ref,  # Ensure single Reference object
                type=CodeableConcept(
                    coding=[
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
                            code="EHCPOL",
                            display="Extended healthcare"
                        )
                    ]
                )
            )
            
            logger.info("Successfully mapped Coverage resource")
            return coverage
            
        except Exception as e:
            logger.error(f"Failed to map coverage: {str(e)}")
            raise FHIRMappingError(f"Coverage mapping failed: {str(e)}")
    
    def _map_organization(self, edi_data) -> Organization:
        """Map X12 278 organization information to FHIR Organization resource."""
        try:
            # Extract organization data from 2000A/2010AA loops (information source)
            org_segment = self._find_segment(edi_data.segments, "NM1", qualifier="PR")
            
            organization = Organization(
                id=str(uuid.uuid4()),
                meta=Meta(
                    profile=["http://hl7.org/fhir/us/davinci-pas/StructureDefinition/profile-insurer"]
                ),
                active=True
            )
            
            if org_segment:
                org_parts = org_segment.elements
                if len(org_parts) >= 3:
                    organization.name = org_parts[2]  # Organization name
                
                # Add organization identifier
                if len(org_parts) >= 9:
                    organization.identifier = [
                        Identifier(
                            type=CodeableConcept(
                                coding=[
                                    Coding(
                                        system="http://terminology.hl7.org/CodeSystem/v2-0203",
                                        code="NIIP",
                                        display="National Insurance Payor Identifier (Payor)"
                                    )
                                ]
                            ),
                            value=org_parts[8],
                            system="http://hl7.org/fhir/sid/us-npi"
                        )
                    ]
            else:
                organization.name = "Default Healthcare Organization"
            
            return organization
            
        except Exception as e:
            self.logger.error(f"Failed to map organization: {str(e)}")
            raise FHIRMappingError(f"Organization mapping failed: {str(e)}")
    
    def _map_practitioner(self, edi_data) -> Practitioner:
        """Map X12 278 practitioner information to FHIR Practitioner resource."""
        try:
            # Extract practitioner data from 2000B/2010BA loops (information receiver)
            prac_segment = self._find_segment(edi_data.segments, "NM1", qualifier="82")
            
            practitioner = Practitioner(
                id=str(uuid.uuid4()),
                meta=Meta(
                    profile=["http://hl7.org/fhir/us/davinci-pas/StructureDefinition/profile-practitioner"]
                )
            )
            
            if prac_segment:
                prac_parts = prac_segment.elements
                if len(prac_parts) >= 4:
                    practitioner.name = [
                        HumanName(
                            family=prac_parts[2] if len(prac_parts) > 2 else "",
                            given=[prac_parts[3]] if len(prac_parts) > 3 else []
                        )
                    ]
                
                # Add practitioner identifier (NPI)
                if len(prac_parts) >= 9:
                    practitioner.identifier = [
                        Identifier(
                            type=CodeableConcept(
                                coding=[
                                    Coding(
                                        system="http://terminology.hl7.org/CodeSystem/v2-0203",
                                        code="NPI",
                                        display="National Provider Identifier"
                                    )
                                ]
                            ),
                            value=prac_parts[8],
                            system="http://hl7.org/fhir/sid/us-npi"
                        )
                    ]
            else:
                practitioner.name = [
                    HumanName(
                        family="Unknown",
                        given=["Provider"]
                    )
                ]
            
            return practitioner
            
        except Exception as e:
            self.logger.error(f"Failed to map practitioner: {str(e)}")
            raise FHIRMappingError(f"Practitioner mapping failed: {str(e)}")
    
    def _map_coverage_eligibility_request(
        self,
        edi_data,
        patient: Patient,
        coverage: Coverage,
        organization: Organization,
        practitioner: Practitioner
    ) -> CoverageEligibilityRequest:
        """
        Map X12 278 to FHIR CoverageEligibilityRequest - the main resource for prior auth.
        
        This is the correct FHIR resource for X12 278 prior authorization requests
        as specified in the Da Vinci PAS Implementation Guide.
        """
        try:
            # Find BHT segment for transaction details
            bht_segment = self._find_segment(edi_data.segments, "BHT")
            
            # Create CoverageEligibilityRequest
            request = CoverageEligibilityRequest(
                id=str(uuid.uuid4()),
                status="active",
                priority=CodeableConcept(
                    coding=[Coding(
                        system="http://terminology.hl7.org/CodeSystem/processpriority",
                        code="normal"
                    )]
                ),
                purpose=["auth-requirements"],
                patient=Reference(reference=f"Patient/{patient.id}"),
                created=datetime.utcnow().isoformat() + "Z",  # Fixed: timezone-aware datetime
                provider=Reference(reference=f"Practitioner/{practitioner.id}"),
                insurer=Reference(reference=f"Organization/{organization.id}"),
                insurance=[{
                    "focal": True,
                    "coverage": Reference(reference=f"Coverage/{coverage.id}")
                }]
            )
            
            # Parse BHT segment for transaction details
            if bht_segment:
                bht_parts = bht_segment.elements
                if len(bht_parts) >= 4:
                    # Set identifier from BHT reference number
                    request.identifier = [
                        Identifier(
                            type=CodeableConcept(
                                coding=[
                                    Coding(
                                        system="http://terminology.hl7.org/CodeSystem/v2-0203",
                                        code="PLAC",
                                        display="Placer Identifier"
                                    )
                                ]
                            ),
                            value=bht_parts[3],  # BHT03 - Reference Identification
                            system="http://example.org/prior-auth-id"
                        )
                    ]
            
            # Add service categories from UM segments
            um_segments = self._find_all_segments(edi_data.segments, "UM")
            if um_segments:
                items = []
                for i, um_segment in enumerate(um_segments):
                    if um_segment.elements and len(um_segment.elements) >= 2:
                        items.append({
                            "category": CodeableConcept(
                                coding=[
                                    Coding(
                                        system="https://x12.org/codes/service-type-codes",
                                        code=um_segment.elements[1],  # UM02 - Service Type Code
                                        display=f"Service Type {um_segment.elements[1]}"
                                    )
                                ]
                            )
                        })
                
                if items:
                    request.item = items
            
            return request
            
        except Exception as e:
            self.logger.error(f"Failed to map CoverageEligibilityRequest: {str(e)}")
            raise FHIRMappingError(f"CoverageEligibilityRequest mapping failed: {str(e)}")
    
    def _find_segment(self, segments, segment_id: str, qualifier: str = None):
        """Find first segment matching ID and optional qualifier."""
        for segment in segments:
            # Handle both ParsedEDI segment objects and dicts robustly
            if hasattr(segment, 'segment_id'):
                # EDISegment object
                seg_id = segment.segment_id
                elements = segment.elements
            elif hasattr(segment, 'tag'):
                # Legacy object with tag attribute
                seg_id = segment.tag
                elements = getattr(segment, 'elements', [])
            elif isinstance(segment, dict):
                # Dictionary format
                seg_id = segment.get('tag', '') or segment.get('segment_id', '')
                elements = segment.get('elements', [])
            else:
                # Unknown format, skip
                continue
            
            if seg_id == segment_id:
                if qualifier is None:
                    return segment
                else:
                    # Check qualifier in elements
                    if elements and len(elements) > 0 and elements[0] == qualifier:
                        return segment
        return None
    
    def _find_all_segments(self, segments, segment_id: str):
        """Find all segments matching the given segment ID."""
        result = []
        for segment in segments:
            # Handle both ParsedEDI segment objects and dicts robustly
            if hasattr(segment, 'segment_id'):
                # EDISegment object
                seg_id = segment.segment_id
            elif hasattr(segment, 'tag'):
                # Legacy object with tag attribute
                seg_id = segment.tag
            elif isinstance(segment, dict):
                # Dictionary format
                seg_id = segment.get('tag', '') or segment.get('segment_id', '')
            else:
                # Unknown format, skip
                continue
                
            if seg_id == segment_id:
                result.append(segment)
        return result


class FHIRToX12Mapper:
    """
    Maps FHIR CoverageEligibilityResponse resources back to X12 278 EDI format.
    
    This mapper handles the reverse transformation from FHIR back to EDI
    for prior authorization responses and other data exchange scenarios.
    """
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def map_to_x12(self, fhir_bundle: Dict[str, Any]) -> str:
        """
        Map FHIR CoverageEligibilityResponse bundle back to X12 278 EDI format.
        
        Args:
            fhir_bundle: FHIR bundle containing CoverageEligibilityResponse
            
        Returns:
            X12 278 EDI formatted string
        """
        try:
            self.logger.info("Starting FHIR to X12 278 EDI mapping")
            
            # Parse FHIR bundle
            bundle_data = fhir_bundle
            entries = bundle_data.get("entry", [])
            
            # Find main CoverageEligibilityResponse resource
            coverage_response = None
            for entry in entries:
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "CoverageEligibilityResponse":
                    coverage_response = resource
                    break
            
            if not coverage_response:
                raise FHIRMappingError("No CoverageEligibilityResponse found in bundle")
            
            # Build X12 278 response
            x12_segments = []
            
            # ISA segment (Interchange Header)
            x12_segments.append(self._build_isa_segment())
            
            # GS segment (Functional Group Header)
            x12_segments.append(self._build_gs_segment())
            
            # ST segment (Transaction Set Header)
            x12_segments.append("ST*278*0001~")
            
            # BHT segment (Beginning of Hierarchical Transaction)
            x12_segments.append(self._build_bht_segment(coverage_response))
            
            # 2000A HL segment (Information Source Level)
            x12_segments.append("HL*1**20*1~")
            
            # 2000B HL segment (Information Receiver Level)
            x12_segments.append("HL*2*1*21*1~")
            
            # 2000C HL segment (Subscriber Level)
            x12_segments.append("HL*3*2*22*0~")
            
            # Add response segments based on FHIR data
            x12_segments.extend(self._build_response_segments(coverage_response))
            
            # SE segment (Transaction Set Trailer)
            x12_segments.append(f"SE*{len(x12_segments) + 1}*0001~")
            
            # GE segment (Functional Group Trailer)
            x12_segments.append("GE*1*1~")
            
            # IEA segment (Interchange Trailer)
            x12_segments.append("IEA*1*000000001~")
            
            x12_output = "".join(x12_segments)
            
            self.logger.info("Successfully mapped FHIR to X12 278 EDI")
            return x12_output
            
        except Exception as e:
            self.logger.error(f"FHIR to X12 mapping failed: {str(e)}")
            raise FHIRMappingError(f"Failed to map FHIR to X12: {str(e)}")
    
    def _build_isa_segment(self) -> str:
        """Build ISA (Interchange Header) segment."""
        timestamp = datetime.now().strftime("%y%m%d%H%M")
        return (
            f"ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *"
            f"{timestamp[:6]}*{timestamp[6:]}*U*00501*000000001*0*P*>~"
        )
    
    def _build_gs_segment(self) -> str:
        """Build GS (Functional Group Header) segment."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        return f"GS*HS*SENDER*RECEIVER*{timestamp[:8]}*{timestamp[8:]}*1*X*005010X279A1~"
    
    def _build_bht_segment(self, coverage_response: Dict[str, Any]) -> str:
        """Build BHT (Beginning of Hierarchical Transaction) segment."""
        # Extract request identifier
        request_id = "0001"
        identifiers = coverage_response.get("identifier", [])
        if identifiers and len(identifiers) > 0:
            request_id = identifiers[0].get("value", "0001")
        
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"BHT*0078*00*{request_id}*{timestamp}*{datetime.now().strftime('%H%M')}~"
    
    def _build_response_segments(self, coverage_response: Dict[str, Any]) -> List[str]:
        """Build response-specific segments based on FHIR CoverageEligibilityResponse."""
        segments = []
        
        # AAA segment (Request Validation)
        outcome = coverage_response.get("outcome", "complete")
        if outcome == "complete":
            segments.append("AAA*Y**85~")  # Valid request
        else:
            segments.append("AAA*N**85~")  # Invalid request
        
        # EB segments (Eligibility or Benefit Information)
        insurance_items = coverage_response.get("insurance", [])
        for insurance in insurance_items:
            items = insurance.get("item", [])
            for item in items:
                benefit = item.get("benefit", [])
                if benefit:
                    segments.append("EB*1**30~")  # Active coverage
        
        return segments


# Factory function for getting appropriate mapper
def get_fhir_mapper(direction: str = "to_fhir"):
    """
    Factory function to get appropriate FHIR mapper.
    
    Args:
        direction: 'to_fhir' for X12->FHIR, 'to_x12' for FHIR->X12
        
    Returns:
        Appropriate mapper instance
    """
    if direction == "to_fhir":
        return X12To278FHIRMapper()
    elif direction == "to_x12":
        return FHIRToX12Mapper()
    else:
        raise ValueError(f"Unknown mapping direction: {direction}")


# Export main classes
__all__ = [
    "X12To278FHIRMapper",
    "FHIRToX12Mapper", 
    "FHIRMappingError",
    "get_fhir_mapper"
] 