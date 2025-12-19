# Contributing to Exotel Voice Bot Framework

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/exotel-voice-bot.git`
3. Create a branch: `git checkout -b feature/your-feature-name`

## How to Contribute

### Reporting Bugs

- Use the [Bug Report](https://github.com/YOUR_ORG/exotel-voice-bot/issues/new?template=bug_report.md) template
- Include steps to reproduce
- Include expected vs actual behavior
- Include logs if applicable

### Suggesting Features

- Use the [Feature Request](https://github.com/YOUR_ORG/exotel-voice-bot/issues/new?template=feature_request.md) template
- Describe the use case
- Explain why this would be valuable

### Adding a New Bot

1. Create your bot in `examples/`
2. Follow the existing bot structure
3. Use shared utilities from `src/utils/botUtils.js`
4. Add npm script in `package.json`
5. Update README.md with bot description
6. Add tests in `tests/`

## Development Setup

```bash
# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Run tests
npm test

# Run linting
npm run lint

# Start development
npm run dev
```

## Pull Request Process

1. **Update documentation** for any new features
2. **Add tests** for new functionality
3. **Run all tests**: `npm test`
4. **Run linting**: `npm run lint`
5. **Update CHANGELOG.md** with your changes
6. **Fill out the PR template** completely

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No sensitive data (API keys, tokens) in code

## Coding Standards

### JavaScript/TypeScript

- Use ES6+ features
- Use async/await over callbacks
- Use meaningful variable names
- Add JSDoc comments for functions

### Naming Conventions

- Files: `kebab-case.js`
- Classes: `PascalCase`
- Functions/Variables: `camelCase`
- Constants: `UPPER_SNAKE_CASE`

### Bot Structure

```javascript
class MyBot extends ExotelWSSServer {
  constructor() {
    super();
    this.sessions = new Map();
    // Initialize AI clients
  }

  initializeSession(streamId) {
    // Return session object
  }

  getMessageCallbacks(streamId, ws, sender) {
    return {
      onStart: async (streamInfo) => { /* ... */ },
      onMedia: (mediaData) => { /* ... */ },
      onStop: (stopData) => { /* ... */ }
    };
  }
}
```

### Audio Handling

- Always use 3200-byte chunks for Exotel
- Use `AudioResampler` for sample rate conversion
- Use `AudioUtils` from `botUtils.js`

### Error Handling

- Always catch and log errors
- Clean up resources on failure
- Send user-friendly error messages

## Questions?

Open an issue or reach out to the maintainers.

---

Thank you for contributing! 🙏

