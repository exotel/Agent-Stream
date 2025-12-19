module.exports = {
  env: {
    node: true,
    es2022: true,
    jest: true
  },
  extends: [
    'eslint:recommended'
  ],
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module'
  },
  rules: {
    // Error prevention
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    'no-console': 'off', // Allow console for logging
    'no-undef': 'error',
    
    // Best practices
    'eqeqeq': ['error', 'always'],
    'no-eval': 'error',
    'no-implied-eval': 'error',
    'no-new-func': 'error',
    'no-return-await': 'warn',
    'require-await': 'warn',
    
    // Style (relaxed for flexibility)
    'semi': ['warn', 'always'],
    'quotes': ['warn', 'single', { avoidEscape: true }],
    'indent': ['warn', 2, { SwitchCase: 1 }],
    'comma-dangle': ['warn', 'never'],
    'no-trailing-spaces': 'warn',
    'no-multiple-empty-lines': ['warn', { max: 2 }],
    
    // Node.js specific
    'no-process-exit': 'off', // Allow process.exit in CLI scripts
    'handle-callback-err': 'warn'
  },
  overrides: [
    {
      files: ['tests/**/*.js', '**/*.test.js', '**/*.spec.js'],
      rules: {
        'no-unused-vars': 'off'
      }
    }
  ],
  ignorePatterns: [
    'node_modules/',
    'dist/',
    'coverage/',
    '*.min.js'
  ]
};

