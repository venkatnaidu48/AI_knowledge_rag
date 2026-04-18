#!/usr/bin/env python
"""
🚀 PRACTICAL: Upload Documents to Your RAG System
Ready-to-run examples with error handling
"""

import requests
import json
import time
import sys
from pathlib import Path
from typing import Optional, Dict

print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║               📤 DOCUMENT UPLOAD TO YOUR RAG SYSTEM                         ║
║                                                                              ║
║                    Practical Working Examples                               ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

# Configuration
API_URL = "http://localhost:8000"
UPLOAD_ENDPOINT = f"{API_URL}/api/v1/documents/upload"
LIST_ENDPOINT = f"{API_URL}/api/v1/documents/list"

# Helper function to check if server is running
def check_server():
    """Check if RAG server is running"""
    try:
        response = requests.get(API_URL, timeout=2)
        return True
    except:
        print(f"❌ ERROR: Cannot connect to {API_URL}")
        print(f"\n   Make sure your RAG application is running:")
        print(f"   $ python run.py")
        return False

# ============================================================================
# EXAMPLE 1: Upload a Single Document
# ============================================================================

def example_1_basic_upload():
    """Example 1: Upload one document (simplest approach)"""
    
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Single Document Upload")
    print("="*80 + "\n")
    
    print("""
    This example uploads ONE document to your RAG system.
    The document becomes searchable in ~5 seconds.
    """)
    
    # First, check if server is running
    if not check_server():
        return
    
    print("📄 Creating test document...\n")
    
    # Create a sample document to upload
    sample_doc = "knowledge_base/annual_report_2024.txt"
    
    if not Path(sample_doc).exists():
        print(f"⚠️  Sample document not found: {sample_doc}")
        print("Creating a test document instead...\n")
        
        # Create a small test document
        test_file = "test_document.txt"
        with open(test_file, "w") as f:
            f.write("""
        Company Annual Report 2024
        
        Executive Summary:
        Our company achieved record revenue of $500 million in 2024,
        representing a 25% year-over-year growth. We expanded into
        three new markets and launched five innovative products.
        
        Key Achievements:
        - Revenue: $500M (+25% YoY)
        - Employee count: 5,000 (+500 this year)
        - New products: 5 launched
        - Market expansion: 3 new regions
        - Customer satisfaction: 92%
        
        Financial Highlights:
        - Net profit margin: 15%
        - Return on equity: 22%
        - Debt-to-equity ratio: 0.8
        - Cash reserves: $100M
        """)
        sample_doc = test_file
        print(f"✅ Created test file: {test_file}\n")
    
    print(f"📤 Uploading: {sample_doc}")
    print("-" * 80)
    
    try:
        # Open and upload the file
        with open(sample_doc, "rb") as f:
            response = requests.post(
                UPLOAD_ENDPOINT,
                files={"file": f},
                data={
                    "department": "Finance",
                    "sensitivity": "internal"
                }
            )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success"):
                print(f"\n✅ UPLOAD SUCCESSFUL!\n")
                print(f"   Document ID:     {result['document_id']}")
                print(f"   Filename:        {result['name']}")
                print(f"   Chunks created:  {result['chunks_created']}")
                print(f"   File size:       {result['file_size_bytes']:,} bytes")
                print(f"   Quality score:   {result['quality_score']:.0%}")
                print(f"\n   ⏱️  Document is NOW SEARCHABLE in your RAG system!")
            else:
                print(f"\n❌ Upload failed:")
                print(f"   {result.get('errors')}")
        else:
            print(f"\n❌ Server error: {response.status_code}")
            print(f"   {response.text}")
    
    except FileNotFoundError:
        print(f"❌ File not found: {sample_doc}")
    except Exception as e:
        print(f"❌ Error: {e}")

# ============================================================================
# EXAMPLE 2: Upload with Metadata
# ============================================================================

def example_2_upload_with_metadata():
    """Example 2: Upload document with additional metadata"""
    
    print("\n" + "="*80)
    print("EXAMPLE 2: Upload with Metadata (Department, Owner, Security Level)")
    print("="*80 + "\n")
    
    print("""
    This example shows how to tag documents with metadata:
    - Department (e.g., Finance, HR, Sales)
    - Owner email (who uploaded it)
    - Sensitivity level (public, internal, confidential)
    
    Metadata helps organize and control access to documents.
    """)
    
    if not check_server():
        return
    
    # Create sample documents with different metadata
    documents = [
        {
            "file": "sample_policy.txt",
            "content": """
        Work From Home Policy 2024
        
        Eligibility: All full-time employees
        Frequency: Up to 3 days per week
        Manager approval required
        Must maintain core hours 10am-3pm
        
        Benefits:
        - Increased productivity
        - Flexible work arrangements
        - Better work-life balance
        """,
            "department": "HR",
            "sensitivity": "internal",
            "owner": "hr@company.com"
        },
        {
            "file": "sample_security.txt",
            "content": """
        Data Security Policy
        
        Access Control:
        - Multi-factor authentication required
        - Role-based access control
        - Least privilege principle
        
        Encryption:
        - TLS 1.3 for all data in transit
        - AES-256 for data at rest
        - End-to-end encryption for sensitive data
        
        Audit Logging:
        - All access logged
        - Retention: 2 years
        - Regular compliance reviews
        """,
            "department": "Security",
            "sensitivity": "confidential",
            "owner": "security@company.com"
        }
    ]
    
    print(f"📄 Creating {len(documents)} test documents...\n")
    
    for doc_info in documents:
        filename = doc_info["file"]
        
        # Create the test file
        with open(filename, "w") as f:
            f.write(doc_info["content"])
        
        print(f"📤 Uploading: {filename}")
        print(f"   Department:  {doc_info['department']}")
        print(f"   Sensitivity: {doc_info['sensitivity']}")
        print(f"   Owner:       {doc_info['owner']}")
        print()
        
        try:
            with open(filename, "rb") as f:
                response = requests.post(
                    UPLOAD_ENDPOINT,
                    files={"file": f},
                    data={
                        "department": doc_info["department"],
                        "sensitivity": doc_info["sensitivity"],
                        "owner_email": doc_info["owner"]
                    }
                )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"   ✅ {result['chunks_created']} chunks created")
                    print(f"   ✅ Document ID: {result['document_id']}")
                else:
                    print(f"   ❌ Failed: {result.get('errors')}")
            else:
                print(f"   ❌ Error: {response.status_code}")
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print()
        time.sleep(1)  # Brief pause between uploads

# ============================================================================
# EXAMPLE 3: Batch Upload Multiple Documents
# ============================================================================

def example_3_batch_upload():
    """Example 3: Upload multiple documents at once"""
    
    print("\n" + "="*80)
    print("EXAMPLE 3: Batch Upload Multiple Documents")
    print("="*80 + "\n")
    
    print("""
    This example uploads multiple documents efficiently.
    Perfect for migrating existing documents to your RAG system.
    """)
    
    if not check_server():
        return
    
    # Create multiple sample documents
    batch_docs = [
        ("product_guide.txt", "Sales", """
        Product Guide 2024
        
        Product A: Enterprise Solution
        - Price: $10,000/month
        - Support: 24/7
        - SLA: 99.9% uptime
        
        Product B: Professional Plan
        - Price: $5,000/month
        - Support: Business hours
        - SLA: 99.5% uptime
        
        Product C: Starter Pack
        - Price: $1,000/month
        - Support: Community forum
        - SLA: 99% uptime
        """),
        
        ("training_manual.txt", "HR", """
        Employee Training Manual
        
        Onboarding Process:
        Day 1: Welcome and orientation
        Day 2-3: System training
        Week 1: Department training
        Week 2: Hands-on practice
        Week 3: Shadowing
        Week 4: Solo work with monitoring
        
        Continuous Learning:
        - Quarterly workshops
        - Annual conferences
        - Online certification programs
        - Mentorship opportunities
        """),
        
        ("market_analysis.txt", "Sales", """
        Market Analysis Report Q1 2024
        
        Market Size:
        Total addressable market: $50 billion
        Serviceable market: $15 billion
        Market growth rate: 12% annually
        
        Competitive Landscape:
        5 major competitors
        20+ smaller players
        High fragmentation
        Consolidation trends
        
        Opportunities:
        - Emerging markets
        - New use cases
        - Integration partnerships
        """)
    ]
    
    print(f"📚 Creating {len(batch_docs)} documents for batch upload...\n")
    
    # Upload all documents
    successful = 0
    failed = 0
    
    for i, (filename, department, content) in enumerate(batch_docs, 1):
        print(f"[{i}/{len(batch_docs)}] {filename}")
        
        # Create the file
        with open(filename, "w") as f:
            f.write(content)
        
        try:
            with open(filename, "rb") as f:
                response = requests.post(
                    UPLOAD_ENDPOINT,
                    files={"file": f},
                    data={"department": department}
                )
            
            if response.status_code == 200 and response.json().get("success"):
                result = response.json()
                print(f"          ✅ {result['chunks_created']} chunks | Quality: {result['quality_score']:.0%}")
                successful += 1
            else:
                print(f"          ❌ Failed")
                failed += 1
        
        except Exception as e:
            print(f"          ❌ Error: {e}")
            failed += 1
        
        time.sleep(0.5)
    
    print(f"\n{'─'*80}")
    print(f"📊 Batch Upload Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed:     {failed}")
    print(f"   📚 Total docs in system: {successful} added this batch")

# ============================================================================
# EXAMPLE 4: List and Verify Uploaded Documents
# ============================================================================

def example_4_list_documents():
    """Example 4: List and verify all uploaded documents"""
    
    print("\n" + "="*80)
    print("EXAMPLE 4: List All Uploaded Documents")
    print("="*80 + "\n")
    
    print("""
    This example shows how to list all documents in your RAG system
    and verify that uploads were successful.
    """)
    
    if not check_server():
        return
    
    print("📚 Fetching document list...\n")
    
    try:
        response = requests.get(LIST_ENDPOINT)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"{'─'*80}")
            print(f"📊 System Statistics:")
            print(f"{'─'*80}")
            print(f"Total documents:  {data.get('total', 0)}")
            print(f"Total chunks:     {data.get('total_chunks', 'N/A')}")
            print(f"Total embeddings: {data.get('total_embeddings', 'N/A')}")
            print(f"\n{'─'*80}")
            print(f"📄 Recent Documents:")
            print(f"{'─'*80}\n")
            
            # Show last 5 documents
            documents = data.get("documents", [])[-5:]
            
            for doc in documents:
                print(f"Document: {doc['name']}")
                print(f"  ID:        {doc['id']}")
                print(f"  Uploaded:  {doc.get('uploaded_at', 'N/A')}")
                print(f"  Status:    {doc.get('status', 'N/A')}")
                print(f"  Chunks:    {doc.get('chunks', 'N/A')}")
                print()
        else:
            print(f"❌ Error: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

# ============================================================================
# EXAMPLE 5: Full Workflow Example
# ============================================================================

def example_5_full_workflow():
    """Example 5: Complete workflow - upload and query"""
    
    print("\n" + "="*80)
    print("EXAMPLE 5: Complete Workflow - Upload Then Query")
    print("="*80 + "\n")
    
    print("""
    This example shows the complete flow:
    1. Upload a document
    2. Verify it's processed
    3. Query the system to test
    """)
    
    if not check_server():
        return
    
    # Step 1: Upload document
    print("STEP 1: Upload Document")
    print("─" * 80)
    
    doc_content = """
    Customer Service Excellence Guide
    
    Our Mission:
    Provide exceptional customer service to build lasting relationships
    
    Core Principles:
    1. Listen actively to customer needs
    2. Respond promptly to inquiries
    3. Exceed expectations
    4. Take ownership of issues
    5. Follow up to ensure satisfaction
    
    Key Metrics:
    - First response time: < 1 hour
    - Resolution time: < 24 hours
    - Customer satisfaction: > 90%
    - Retention rate: > 95%
    """
    
    doc_file = "customer_service_guide.txt"
    with open(doc_file, "w") as f:
        f.write(doc_content)
    
    print(f"Uploading: {doc_file}\n")
    
    try:
        with open(doc_file, "rb") as f:
            response = requests.post(
                UPLOAD_ENDPOINT,
                files={"file": f},
                data={"department": "Customer Success"}
            )
        
        if response.status_code == 200:
            result = response.json()
            doc_id = result["document_id"]
            
            print(f"✅ Upload successful!")
            print(f"   Document ID: {doc_id}")
            print(f"   Chunks created: {result['chunks_created']}")
            print(f"   Quality: {result['quality_score']:.0%}\n")
            
            # Step 2: Verify document
            print("STEP 2: Verify Document is Indexed")
            print("─" * 80)
            
            time.sleep(1)  # Give it a moment to process
            
            response = requests.get(LIST_ENDPOINT)
            if response.status_code == 200:
                docs = response.json()["documents"]
                total = len(docs)
                print(f"✅ System now has {total} documents\n")
                
                # Step 3: Show how to query it
                print("STEP 3: How to Query This Document")
                print("─" * 80)
                
                print(f"""
                You can now ask questions like:
                
                ❓ "What are the key principles of customer service?"
                ❓ "What is our first response time SLA?"
                ❓ "How do we measure customer satisfaction?"
                
                The system will search all {total} documents (including this new one!)
                and return answers based on the most relevant chunks.
                
                Try it with:
                    POST http://localhost:8000/api/v1/chat
                    {{
                        "query": "What are the key customer service principles?"
                    }}
                """)
        else:
            print(f"❌ Error: {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

# ============================================================================
# Main Menu
# ============================================================================

def main():
    """Interactive menu to run examples"""
    
    examples = [
        ("Single Document Upload", example_1_basic_upload),
        ("Upload with Metadata", example_2_upload_with_metadata),
        ("Batch Upload", example_3_batch_upload),
        ("List Documents", example_4_list_documents),
        ("Complete Workflow", example_5_full_workflow),
    ]
    
    print("\n📋 AVAILABLE EXAMPLES:\n")
    for i, (name, _) in enumerate(examples, 1):
        print(f"   {i}. {name}")
    print(f"   0. Run All Examples")
    print(f"   Q. Quit\n")
    
    choice = input("Choose an example (0-5 or Q): ").strip().upper()
    
    if choice == "Q":
        print("\nGoodbye! 👋\n")
        return
    elif choice == "0":
        print("\n🚀 Running all examples...\n")
        for name, func in examples:
            func()
            input("\nPress Enter to continue to next example...")
    elif choice.isdigit() and 0 < int(choice) <= len(examples):
        examples[int(choice) - 1][1]()
    else:
        print("❌ Invalid choice\n")
        main()

if __name__ == "__main__":
    main()
    print("\n✨ Done! Your documents are now searchable in your RAG system! 🚀\n")
