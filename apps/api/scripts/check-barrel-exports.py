#!/usr/bin/env python3
"""
Check barrel export completeness for packages/types/

Validates that all .ts files in packages/types/ are exported from index.ts
"""
import os
from pathlib import Path
# Removed typing import

def check_barrel_exports() -> tuple[bool, list[str]]:
    """
    Check if all TypeScript files in packages/types/ are exported from index.ts
    
    Returns:
        tuple: (is_complete, missing_exports)
    """
    types_dir = Path("packages/types")
    index_file = types_dir / "index.ts"
    
    if not index_file.exists():
        return False, ["index.ts not found"]
    
    # Read index.ts to find exported modules
    with open(index_file) as f:
        content = f.read()
    
    # Extract exports like: export * from "./auth";
    exported_modules = set()
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('export * from'):
            # Extract module name from "./auth";
            module = line.split('"')[1].replace('./', '').replace("'", "")
            exported_modules.add(module)
    
    # Find all .ts files in packages/types (except index.ts and test files)
    all_modules = set()
    for ts_file in types_dir.glob("*.ts"):
        if ts_file.name != "index.ts" and not ts_file.name.endswith(".test.ts"):
            all_modules.add(ts_file.stem)
    
    # Find missing exports
    missing = sorted(all_modules - exported_modules)
    
    return len(missing) == 0, missing

if __name__ == "__main__":
    is_complete, missing = check_barrel_exports()
    
    if is_complete:
        print("✅ All TypeScript files are exported from packages/types/index.ts")
        exit(0)
    else:
        print(f"❌ Missing exports for: {', '.join(missing)}")
        print("\nAdd these lines to packages/types/index.ts:")
        for module in missing:
            print(f'export * from "./{module}";')
        exit(1)
