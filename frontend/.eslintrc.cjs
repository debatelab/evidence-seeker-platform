/* ESLint configuration for React + TypeScript + Vite */
module.exports = {
  root: true,
  env: {
    browser: true,
    es2023: true,
    node: true,
  },
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: { jsx: true },
  },
  settings: {
    react: { version: 'detect' },
  },
  plugins: ['@typescript-eslint', 'react', 'react-hooks'],
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:@typescript-eslint/stylistic',
  ],
  rules: {
    'react/react-in-jsx-scope': 'off', // Not needed with React 17+
    'react/prop-types': 'off', // Using TypeScript for typing
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    // Transitional relaxations (to be re-tightened after refactor):
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/array-type': ['warn', { default: 'array-simple' }],
    // Allow unused vars that start with underscore (intentional ignore)
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
    // React specific tweaks
    'react/no-unescaped-entities': 'warn',
    "@typescript-eslint/consistent-type-definitions": "off"
  },
  overrides: [
    {
      files: ['**/*.test.{ts,tsx}'],
      env: { jest: true },
    },
  ],
};
