import tseslint from "@typescript-eslint/eslint-plugin";
import tsparser from "@typescript-eslint/parser";

export default [
  {
    files: ["**/*.ts"],
    languageOptions: {
      parser: tsparser,
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: "module",
        project: "./tsconfig.json",
      },
    },
    plugins: {
      "@typescript-eslint": tseslint,
    },
    rules: {
      // ===================================================================
      // ASYNC/AWAIT RULES - Prevent issues like the collection icons bug
      // ===================================================================

      // ERROR: Missing await on promises
      "@typescript-eslint/no-floating-promises": [
        "error",
        {
          ignoreVoid: true,
          ignoreIIFE: false,
        },
      ],

      // ERROR: Returning promise without await in async function
      "@typescript-eslint/return-await": ["error", "always"],

      // ERROR: Using await on non-promise values
      "@typescript-eslint/await-thenable": "error",

      // WARN: Async function with no await (downgraded to warning)
      "@typescript-eslint/require-await": "warn",

      // WARN: Promise in void context (downgraded for Express compatibility)
      "@typescript-eslint/no-misused-promises": [
        "warn",
        {
          checksConditionals: true,
          checksVoidReturn: {
            arguments: false, // Allow async functions as Express handlers
            attributes: true,
            properties: true,
            returns: true,
            variables: true,
          },
        },
      ],

      // OFF: Promise function async (not critical for our use case)
      "@typescript-eslint/promise-function-async": "off",

      // WARN: Console statements (useful for production)
      "no-console": [
        "warn",
        {
          allow: ["warn", "error"],
        },
      ],

      // ERROR: Unused variables (except those prefixed with _)
      "@typescript-eslint/no-unused-vars": [
        "error",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],

      // WARN: Any type usage (downgraded to warning)
      "@typescript-eslint/no-explicit-any": "warn",

      // OFF: Allow empty interfaces (used for type extensions)
      "@typescript-eslint/no-empty-interface": "off",

      // OFF: Allow non-null assertions (! operator) - sometimes needed
      "@typescript-eslint/no-non-null-assertion": "off",

      // WARN: Unsafe member access (downgraded - too strict for HA API)
      "@typescript-eslint/no-unsafe-member-access": "warn",

      // WARN: Unsafe call (downgraded - too strict for HA API)
      "@typescript-eslint/no-unsafe-call": "warn",

      // WARN: Unsafe assignment (downgraded - too strict for HA API)
      "@typescript-eslint/no-unsafe-assignment": "warn",

      // WARN: Unsafe return (downgraded - too strict for HA API)
      "@typescript-eslint/no-unsafe-return": "warn",
    },
  },
  {
    ignores: ["node_modules/", "dist/", "**/*.js", "**/*.d.ts"],
  },
];
