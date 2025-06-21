#!/usr/bin/env python3
"""Quick test to verify system fixes."""

import asyncio
from app.services.processor import EDIProcessingService
from app.core.models import EDIFileUpload

async def test_fixes():
    print("=== Testing Fixed System ===")
    
    processor = EDIProcessingService()
    
    # Test with fixed EDI content
    content = """ISA*00*          *00*          *ZZ*SENDER_ID     *ZZ*RECEIVER_ID   *250620*1909*U*00501*000000001*0*P*>~
GS*HS*SENDER*RECEIVER*20250620*1909*1*X*005010X279A1~
ST*278*0001~
BHT*0078*00*REF123*20250620*1909~
HL*1**20*1~
NM1*PR*2*INSURANCE COMPANY*****PI*12345~
HL*2*1*21*1~
NM1*82*1*PROVIDER*LAST*FIRST***XX*9876543210~
HL*3*2*22*0~
NM1*IL*1*PATIENT*LAST*FIRST***MI*MEMBER123~
DMG*D8*19800101*M~
SE*11*0001~
GE*1*1~
IEA*1*000000001~"""
    
    upload_request = EDIFileUpload(
        filename='test_fixed.edi',
        content_type='text/plain',
        validate_only=False,
        enable_ai_analysis=True,
        output_format='fhir'
    )
    
    try:
        job = await processor.process_content(content, upload_request)
        
        print(f"Job ID: {job.job_id}")
        print(f"Status: {job.status}")
        print(f"Parsed EDI: {'✅ SUCCESS' if job.parsed_edi else '❌ FAILED'}")
        print(f"Validation: {'✅ SUCCESS' if job.validation_result else '❌ FAILED'}")
        print(f"FHIR Mapping: {'✅ SUCCESS' if job.fhir_mapping else '❌ FAILED'}")
        print(f"AI Analysis: {'✅ SUCCESS' if job.ai_analysis else '❌ FAILED'}")
        
        if job.fhir_mapping:
            print(f"FHIR Resources: {len(job.fhir_mapping.resources)}")
            
        if job.validation_result:
            print(f"Validation Valid: {job.validation_result.is_valid}")
            print(f"Segments Validated: {job.validation_result.segments_validated}")
            
        print(f"\n✅ SYSTEM TEST: {'PASSED' if job.fhir_mapping and job.validation_result else 'FAILED'}")
        
        return job.fhir_mapping is not None and job.validation_result is not None
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_fixes())
    exit(0 if result else 1) 