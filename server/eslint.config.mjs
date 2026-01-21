import tseslint from '@typescript-eslint/eslint-plugin';
import tsparser from '@typescript-eslint/parser';

export default [
  {
    files: ['**/*.ts'],
    languageOptions: {
      parser: tsparser,
      parserOptions: {
        ecmaVersion: 2022,
        sourceType: 'module',
        project: './tsconfig.json',
      },
    },
    plugins: {
      '@typescript-eslint': tseslint,
    },
    rules: {
      // ===================================================================
      // ASYNC/AWAIT RULES - Prevent issues like the collection icons bug
      // ===================================================================

      // ERROR: Missing await on promises
      '@typescript-eslint/no-floating-promises': ['error', {
        ignoreVoid: true,
        ignoreIIFE: false,
      }],

      // ERROR: Returning promise without await in async function
      '@typescript-eslint/return-await': ['error', 'always'],

      // ERROR: Using await on non-promise values
      '@typescript-eslint/await-thenable': 'error',

      // ERROR: Async function with no await
      '@typescript-eslint/require-await': 'error',

      // ERROR: Promise executor function is async
      '@typescript-eslint/no-misused-promises': ['error', {
        checksConditionals: true,
        checksVoidReturn: true,
      }],

      // ERROR: Incorrect Promise.all/race usage
      '@typescript-eslint/promise-function-async': ['error', {
        checkArrowFunctions: true,
        checkFunctionDeclarations: true,
        checkFunctionExpressions: true,
        checkMethodDeclarations: true,
      }],

      // WARN: Console statements (useful for production)
      'no-console': ['warn', {
        allow: ['warn', 'error'],
      }],

      // ERROR: Unused variables (except those prefixed with _)
      '@typescript-eslint/no-unused-vars': ['error', {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        caughtErrorsIgnorePattern: '^_',
      }],

      // WARN: Any type usage
      '@typescript-eslint/no-explicit-any': 'warn',

      // OFF: Allow empty interfaces (used for type extensions)
      '@typescript-eslint/no-empty-interface': 'off',

      // OFF: Allow non-null assertions (! operator) - sometimes needed
      '@typescript-eslint/no-non-null-assertion': 'off',

      // ERROR: Unsafe member access
      '@typescript-eslint/no-unsafe-member-access': 'error',

      // ERROR: Unsafe call
      '@typescript-eslint/no-unsafe-call': 'error',

      // ERROR: Unsafe assignment
      '@typescript-eslint/no-unsafe-assignment': 'error',

      // ERROR: Unsafe return
      '@typescript-eslint/no-unsafe-return': 'error',
    },
  },
  {
    ignores: ['node_modules/', 'dist/', '**/*.js', '**/*.d.ts'],
  },
];
