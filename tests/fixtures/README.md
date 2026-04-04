# Test PDF Fixtures

This directory contains PDF files for testing knowledge ingestion.

## Files

| File | Purpose | Expected Behavior |
|------|---------|-------------------|
| `sample.pdf` | Valid text-extractable PDF | ✅ Should ingest successfully |
| `encrypted.pdf` | Password-protected PDF (simulated) | ❌ Should reject with "password-protected" error |
| `scanned.pdf` | Image-only PDF (no text) | ❌ Should reject with "no extractable text" error |
| `multi-page.pdf` | Multi-page document | ✅ Should create chunks with page metadata |
| `corrupted.pdf` | Invalid PDF format | ❌ Should reject with "invalid format" error |

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

**Password:** `test123` (Note: Current implementation is simulated)

## Regenerating Fixtures

Run: `node tests/fixtures/create-fixtures.js`
