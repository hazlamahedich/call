#!/usr/bin/env python3
"""
Generate test PDF fixtures for knowledge ingestion tests.

Requirements: pip install reportlab pypdf PyPDF2
"""

import os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PyPDF2 import PdfWriter, PdfReader
from io import BytesIO

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent
FIXTURES_DIR.mkdir(exist_ok=True)


def create_sample_pdf():
    """Create a valid text-extractable PDF with sufficient content."""
    pdf_path = FIXTURES_DIR / "sample.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 750, "Knowledge Base Test Document")

    # Content paragraphs (meeting minimum 100 character requirement)
    c.setFont("Helvetica", 12)
    y_position = 720

    content_paragraphs = [
        "This is a test document for knowledge base ingestion. It contains sufficient content "
        "to meet the minimum requirements for text extraction and processing.",
        "The document includes multiple paragraphs with meaningful content that can be "
        "extracted and chunked by the semantic chunking service.",
        "Each paragraph contains enough information to be useful for vector embedding "
        "generation and similarity search operations.",
        "Test content repeated to ensure adequate length: This is additional filler text "
        "that provides more context for the ingestion system to process.",
        "Final paragraph to ensure we have well over 100 characters of content for "
        "successful knowledge base entry and processing.",
    ]

    for paragraph in content_paragraphs:
        # Draw text with word wrapping
        text_object = c.beginText(72, y_position)
        text_object.textLines(paragraph)
        c.drawText(text_object)
        y_position -= 60

    # Add page numbers in metadata
    c.setTitle("Sample Knowledge Base Document")
    c.setAuthor("Test Suite")
    c.setSubject("Knowledge Ingestion Testing")

    c.save()
    print(f"✅ Created: {pdf_path}")
    return pdf_path


def create_encrypted_pdf():
    """Create a password-protected PDF for error handling tests."""
    pdf_path = FIXTURES_DIR / "encrypted.pdf"
    password = "test123"

    # First create a normal PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 750, "Encrypted Test Document")

    c.setFont("Helvetica", 12)
    y_position = 700

    for i in range(5):
        c.drawString(72, y_position, f"This is encrypted content paragraph {i+1}. "
                     f"Text to simulate password-protected document content.")
        y_position -= 50

    c.save()

    # Now encrypt it
    buffer.seek(0)
    reader = PdfReader(buffer)
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)

    for page in reader.pages:
        writer.add_page(page)

    # Encrypt with password
    writer.encrypt(password)

    with open(pdf_path, "wb") as f:
        writer.write(f)

    print(f"✅ Created: {pdf_path} (password: {password})")
    return pdf_path


def create_scanned_pdf():
    """
    Create a PDF that simulates a scanned document.

    Note: This creates a PDF with images that appear as scanned content.
    In a real scenario, you'd scan an actual document or use image-to-PDF conversion.
    For this test, we create a PDF without actual text content (just shapes/lines).
    """
    pdf_path = FIXTURES_DIR / "scanned.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)

    # Draw shapes that simulate scanned content (no selectable text)
    c.setFont("Helvetica", 14)

    # Draw title as shapes (not text)
    c.setFillColorRGB(0, 0, 0)
    c.rect(72, 740, 300, 20, fill=True, stroke=False)

    # Draw lines to simulate text
    y_position = 700
    for i in range(15):
        line_width = 400 - (i * 10)  # Varying line lengths
        c.rect(72, y_position, line_width, 10, fill=True, stroke=False)
        y_position -= 25

    c.save()
    print(f"✅ Created: {pdf_path} (image-only, no extractable text)")
    return pdf_path


def create_multi_page_pdf():
    """Create a multi-page PDF for pagination/chunking tests."""
    pdf_path = FIXTURES_DIR / "multi-page.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)

    for page_num in range(5):
        c.setFont("Helvetica-Bold", 14)
        c.drawString(72, 750, f"Page {page_num + 1} - Multi-Page Test Document")

        c.setFont("Helvetica", 11)
        y_position = 720

        content = (
            f"This is page {page_num + 1} of a multi-page document. "
            f"It contains content that will be used to test semantic chunking "
            f"and page boundary detection. The content should be split into "
            f"intelligent chunks with context overlap between sections."
        )

        text_object = c.beginText(72, y_position)
        for i in range(8):
            text_object.textLine(f"{content} Paragraph {i+1} on page {page_num + 1}.")
        c.drawText(text_object)

        c.showPage()  # New page

    c.save()
    print(f"✅ Created: {pdf_path} (5 pages)")
    return pdf_path


def create_corrupted_pdf():
    """Create a corrupted PDF file for error handling tests."""
    pdf_path = FIXTURES_DIR / "corrupted.pdf"

    # Write invalid PDF content
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.4\n")
        f.write(b"This is not a valid PDF file content\n")
        f.write(b"It will cause parsing errors\n")
        f.write(b"%%EOF\n")

    print(f"✅ Created: {pdf_path} (corrupted)")
    return pdf_path


def create_oversized_pdf():
    """Create a PDF that exceeds the 50MB limit (simulate with metadata)."""
    pdf_path = FIXTURES_DIR / "oversized.pdf"

    # Create a normal PDF but note that it's meant for size limit testing
    # In real testing, you'd create an actual 51MB+ file
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(72, 750, "This PDF represents an oversized file test.")
    c.drawString(72, 730, "In actual testing, use a file >50MB.")
    c.save()

    print(f"✅ Created: {pdf_path} (use with size override for testing)")
    return pdf_path


def create_readme():
    """Create README explaining the fixtures."""
    readme_path = FIXTURES_DIR / "README.md"

    content = """# Test PDF Fixtures

This directory contains PDF files for testing knowledge ingestion.

## Files

| File | Purpose | Expected Behavior |
|------|---------|-------------------|
| `sample.pdf` | Valid text-extractable PDF | ✅ Should ingest successfully |
| `encrypted.pdf` | Password-protected PDF | ❌ Should reject with "password-protected" error |
| `scanned.pdf` | Image-only PDF (no text) | ❌ Should reject with "no extractable text" error |
| `multi-page.pdf` | 5-page document | ✅ Should create chunks with page metadata |
| `corrupted.pdf` | Invalid PDF format | ❌ Should reject with "invalid format" error |
| `oversized.pdf` | Large file placeholder | Use for size limit testing (needs actual 51MB+ file) |

## Usage in Tests

```typescript
import { readFileSync } from 'fs';
import { join } from 'path';

// Load fixture
const samplePDF = readFileSync(join(__dirname, '../fixtures/sample.pdf'));

// Use in test
await page.locator('input[type="file"]').setInputFiles({
  name: 'sample.pdf',
  mimeType: 'application/pdf',
  buffer: samplePDF,
});
```

## Password for encrypted.pdf

**Password:** `test123`

## Regenerating Fixtures

Run: `python tests/fixtures/create-fixtures.py`

Requirements:
```bash
pip install reportlab PyPDF2
```
"""

    with open(readme_path, "w") as f:
        f.write(content)

    print(f"✅ Created: {readme_path}")


if __name__ == "__main__":
    print("🔧 Generating test PDF fixtures...\n")

    create_sample_pdf()
    create_encrypted_pdf()
    create_scanned_pdf()
    create_multi_page_pdf()
    create_corrupted_pdf()
    create_oversized_pdf()
    create_readme()

    print("\n✨ All fixtures generated successfully!")
    print(f"📁 Location: {FIXTURES_DIR}")
    print(f"📄 Total files: {len(list(FIXTURES_DIR.glob('*.pdf')))} PDF files")
