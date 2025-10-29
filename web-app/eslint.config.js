import pluginJs from '@eslint/js'
import pluginTanstack from '@tanstack/eslint-plugin-query'
import tseslint from '@typescript-eslint/eslint-plugin'
import tsparser from '@typescript-eslint/parser'
import react from 'eslint-plugin-react'
import pluginReactHooks from 'eslint-plugin-react-hooks'
import pluginReactRefresh from 'eslint-plugin-react-refresh'
import globals from 'globals'

export default [
  {
    ignores: ['dist', 'eslint.config.js', 'node_modules'],
  },
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.es2020,
      },
      parser: tsparser,
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    plugins: {
      '@typescript-eslint': tseslint,
      react,
      'react-hooks': pluginReactHooks,
      '@tanstack/eslint-plugin-query': pluginTanstack,
      'react-refresh': pluginReactRefresh,
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
    rules: {
      ...pluginJs.configs.recommended.rules,
      ...tseslint.configs.recommended.rules,
      ...react.configs.recommended.rules,
      ...react.configs['jsx-runtime'].rules,
      ...pluginReactHooks.configs.recommended.rules,
      ...pluginTanstack.configs['flat/recommended'].rules,

      // React Refresh: Warn when mixing components and non-components in same file
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],

      // Educational rules for beginners - catching common mistakes

      // TypeScript: Prevent use of 'any' type (teaches proper typing)
      // Changed to warning to be more beginner-friendly
      '@typescript-eslint/no-explicit-any': 'warn',

      // React: Require unique keys in lists (prevents rendering bugs)
      'react/jsx-key': 'error',

      // React: Prevent direct state mutations (teaches immutability)
      // Allow props parameter reassignment (common in React)
      'no-param-reassign': 'warn',

      // TypeScript: Catch unused variables (keeps code clean)
      '@typescript-eslint/no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
        },
      ],

      // TypeScript project: Disable React prop-types (TypeScript handles this)
      'react/prop-types': 'off',
      'react/display-name': 'off',

      // Disable no-undef for TypeScript as it's handled by the TypeScript
      // compiler
      'no-undef': 'off',
    },
  },
]
