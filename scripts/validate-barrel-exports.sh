#!/usr/bin/env bash
# Barrel Export Validation Script
# Validates that all barrel (index.ts) exports in the component tree
# reference files that actually exist.
#
# Usage: ./scripts/validate-barrel-exports.sh [directory]
#   directory: defaults to apps/web/src

set -euo pipefail

TARGET_DIR="${1:-apps/web/src}"
ERRORS=0
CHECKED=0

echo "🔍 Scanning barrel exports in $TARGET_DIR..."

while IFS= read -r barrel; do
    DIR="$(dirname "$barrel")"
    EXPORTS=$(grep -oP "(?<=from ['\"]./)[^'\"]+" "$barrel" 2>/dev/null || true)

    while IFS= read -r exp; do
        [ -z "$exp" ] && continue
        CHECKED=$((CHECKED + 1))

        if [ ! -f "$DIR/$exp" ] && [ ! -f "$DIR/$exp.ts" ] && [ ! -f "$DIR/$exp.tsx" ]; then
            echo "❌ $barrel: './$exp' does not resolve to a file"
            ERRORS=$((ERRORS + 1))
        fi
    done <<< "$EXPORTS"
done < <(find "$TARGET_DIR" -name "index.ts" -not -path "*/node_modules/*" 2>/dev/null)

echo ""
echo "Checked $CHECKED exports across all barrel files."

if [ "$ERRORS" -gt 0 ]; then
    echo "❌ $ERRORS broken export(s) found."
    exit 1
else
    echo "✅ All barrel exports are valid."
    exit 0
fi
