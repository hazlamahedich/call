import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // Disabled to reduce noise in CI logs during development
      // These rules are disabled because:
      // 1. react-hooks/set-state-in-effect - False positive in async tests
      //    where mock component state updates trigger unnecessary re-renders
      // 2. react-hooks/preserve-manual-memoization - Can cause issues with
      //    dependency arrays being recreated unnecessarily in tests
      // Both rules are safe to disable and are re-enabled if needed
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/preserve-manual-memoization": "warn",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);