#!/usr/bin/env node
/**
 * Generate test PDF fixtures for knowledge ingestion tests.
 * Uses basic PDF creation without external dependencies.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FIXTURES_DIR = __dirname;

// Basic PDF creation (minimal valid PDF)
function createMinimalPDF(content, filename) {
  // Very basic PDF structure
  const pdfContent = `%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 4 0 R
>>
>>
/MediaBox [0 0 612 792]
/Contents 5 0 R
>>
endobj
4 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj
5 0 obj
<<
/Length ${content.length}
>>
stream
BT
/F1 12 Tf
50 700 Td
(${content.replace(/\(/g, '\\(').replace(/\)/g, '\\)')}) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000262 00000 n
0000000349 00000 n
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
${content.length + 500}
%%EOF
`;

  fs.writeFileSync(path.join(FIXTURES_DIR, filename), pdfContent);
  console.log(`✅ Created: ${filename}`);
}

// Create test fixtures
function createFixtures() {
  console.log('🔧 Generating test PDF fixtures...\n');

  // 1. Sample PDF with sufficient content
  const sampleContent = `Knowledge Base Test Document

This is a test document for knowledge base ingestion. It contains sufficient content to meet the minimum requirements for text extraction and processing. The document includes multiple paragraphs with meaningful content that can be extracted and chunked by the semantic chunking service. Each paragraph contains enough information to be useful for vector embedding generation and similarity search operations. Test content repeated to ensure adequate length. This is additional filler text that provides more context for the ingestion system to process. Final paragraph to ensure we have well over 100 characters of content for successful knowledge base entry and processing.`;

  createMinimalPDF(sampleContent, 'sample.pdf');

  // 2. Encrypted PDF (note - this won't be actually encrypted without crypto lib, but represents the test case)
  const encryptedContent = `Encrypted Test Document - Password: test123

This document represents a password-protected PDF. In real testing, this would be encrypted using AES-128 or similar encryption. The ingestion system should detect the encryption and reject it with a specific error message about password protection.`;

  createMinimalPDF(encryptedContent, 'encrypted.pdf');

  // 3. Scanned PDF (image-only simulation - minimal text)
  const scannedContent = `[Image-only PDF - No extractable text]`;

  createMinimalPDF(scannedContent, 'scanned.pdf');

  // 4. Multi-page PDF simulation
  const multiPageContent = `Page 1 - Multi-Page Test Document. This is page 1 of a multi-page document. It contains content that will be used to test semantic chunking and page boundary detection. The content should be split into intelligent chunks with context overlap between sections. Page 2 content follows on next page.`;

  createMinimalPDF(multiPageContent, 'multi-page.pdf');

  // 5. Corrupted PDF (invalid format)
  const corruptedPDF = Buffer.from(`%PDF-1.4
This is not a valid PDF file content
It will cause parsing errors
%%EOF
`);

  fs.writeFileSync(path.join(FIXTURES_DIR, 'corrupted.pdf'), corruptedPDF);
  console.log('✅ Created: corrupted.pdf');

  // 6. Create README
  const readme = `# Test PDF Fixtures

This directory contains PDF files for testing knowledge ingestion.

## Files

| File | Purpose | Expected Behavior |
|------|---------|-------------------|
| \`sample.pdf\` | Valid text-extractable PDF | ✅ Should ingest successfully |
| \`encrypted.pdf\` | Password-protected PDF (simulated) | ❌ Should reject with "password-protected" error |
| \`scanned.pdf\` | Image-only PDF (no text) | ❌ Should reject with "no extractable text" error |
| \`multi-page.pdf\` | Multi-page document | ✅ Should create chunks with page metadata |
| \`corrupted.pdf\` | Invalid PDF format | ❌ Should reject with "invalid format" error |

## Usage in Tests

\`\`\`typescript
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
\`\`\`

## Password for encrypted.pdf

**Password:** \`test123\` (Note: Current implementation is simulated)

## Regenerating Fixtures

Run: \`node tests/fixtures/create-fixtures.js\`
`;

  fs.writeFileSync(path.join(FIXTURES_DIR, 'README.md'), readme);
  console.log('✅ Created: README.md');

  console.log('\n✨ All fixtures generated successfully!');
  console.log(`📁 Location: ${FIXTURES_DIR}`);
  console.log(`📄 Total files: ${fs.readdirSync(FIXTURES_DIR).filter(f => f.endsWith('.pdf')).length} PDF files`);
}

createFixtures();
