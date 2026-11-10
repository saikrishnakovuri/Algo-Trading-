# 🛠️ Development Guide

This guide is for developers who want to contribute to or extend the Gemini Dev Assistant.

## Project Architecture

```
gemini-dev-assistant/
├── index.js              # Main CLI interface (520+ lines)
│   ├── mainLoop()        - Interactive CLI loop
│   ├── displayBanner()   - Welcome screen
│   └── displayCommands() - Command help
│
├── gemini.js             # Gemini API integration (180+ lines)
│   ├── initializeGemini()     - Initialize client
│   ├── analyzeCode()          - Send code to Gemini
│   ├── sendPrompt()           - Send custom prompt
│   └── analyzeWithCommand()   - Execute command
│
├── fileReader.js         # File I/O operations (200+ lines)
│   ├── listFiles()      - List supported files
│   ├── readFile()       - Read file with validation
│   ├── writeFile()      - Write to file
│   ├── createBackup()   - Create timestamped backup
│   └── getFileInfo()    - Get file metadata
│
└── utils.js              # Utilities & validators (250+ lines)
    ├── validateApiKey()      - Check API key
    ├── isValidFileType()     - Validate file type
    ├── normalizeCommand()    - Handle command aliases
    ├── getSystemPrompt()     - Get AI instructions
    ├── handleApiError()      - User-friendly errors
    └── formatFileContent()   - Format for display
```

## Code Standards

### ESM Modules
```javascript
// ✅ Use ES modules (import/export)
import { initializeGemini } from "./gemini.js";
export function analyzeCode() { /* ... */ }

// ❌ Don't use CommonJS
const gemini = require("./gemini");
module.exports = { analyzeCode };
```

### Async/Await
```javascript
// ✅ Use async/await for all async operations
async function readFile(path) {
  try {
    const content = await fs.promises.readFile(path, "utf-8");
    return content;
  } catch (error) {
    throw new Error(`Failed to read: ${error.message}`);
  }
}

// ❌ Avoid promise chains
fs.readFile(path, (err, data) => { /* ... */ });
```

### Error Handling
```javascript
// ✅ Throw descriptive errors
if (!apiKey) {
  throw new Error("API key is required. Please check .env file");
}

// ❌ Don't swallow errors
try {
  // code
} catch (error) {
  // Don't just console.log or return silently
}
```

### Comments & Documentation
```javascript
// ✅ Use JSDoc for all functions
/**
 * Analyzes code with specified command
 * @param {string} code - The code to analyze
 * @param {string} command - fix|optimize|explain|refactor
 * @returns {Promise<string>} Analysis result
 * @throws {Error} If API fails
 */
export async function analyzeCode(code, command) {
  // Implementation
}

// ✅ Add inline comments for complex logic
// Check file size before upload (API limit: 1MB)
if (stats.size > 1024 * 1024) {
  throw new Error("File too large");
}
```

## Adding New Features

### 1. Adding a New Command

**Step 1:** Update `getSystemPrompt()` in `utils.js`
```javascript
export function getSystemPrompt(command) {
  const prompts = {
    fix: "...",
    optimize: "...",
    explain: "...",
    refactor: "...",
    test: "You are a test generation expert. Generate unit tests for the provided code." // NEW
  };
  return prompts[command] || prompts.fix;
}
```

**Step 2:** Update command aliases in `normalizeCommand()`
```javascript
export function normalizeCommand(input) {
  const commands = {
    fix: ["fix", "debug", "bug", "repair"],
    optimize: ["optimize", "performance", "improve", "speed"],
    explain: ["explain", "analyze", "understand", "describe"],
    refactor: ["refactor", "clean", "improve", "reorganize"],
    test: ["test", "generate-tests", "unittest"] // NEW
  };
  // ...
}
```

**Step 3:** Update command list in `index.js`
```javascript
const COMMANDS = ["fix", "optimize", "explain", "refactor", "test"]; // Add "test"

function displayCommands() {
  console.log("\n📋 Available Commands:");
  console.log("  • fix      - Find and fix bugs in code");
  console.log("  • optimize - Optimize code for performance");
  console.log("  • explain  - Get detailed explanation of code");
  console.log("  • refactor - Improve code structure and quality");
  console.log("  • test     - Generate unit tests"); // NEW
  console.log("  • exit     - Exit the program\n");
}
```

### 2. Adding Support for New File Types

Edit `isValidFileType()` in `utils.js`:
```javascript
export function isValidFileType(filename) {
  const validExtensions = [
    // ... existing extensions ...
    ".dart",  // Add new extension
    ".elm",
    ".clojure"
  ];
  // ...
}
```

### 3. Adding New Utilities

Create new function in `utils.js` with full JSDoc:
```javascript
/**
 * Converts code to a specific format
 * @param {string} code - Input code
 * @param {string} format - Output format
 * @returns {string} Formatted code
 */
export function convertFormat(code, format) {
  // Implementation
}
```

### 4. Adding API Error Cases

Update `handleApiError()` in `utils.js`:
```javascript
export function handleApiError(error) {
  const message = error.message || "";

  // ... existing error handling ...
  
  if (message.includes("INVALID_ARGUMENT")) {
    return "❌ Invalid argument sent to API. Check code syntax.";
  }

  return `❌ API Error: ${message}`;
}
```

## Testing

### Manual Testing

1. **Test with sample file:**
```bash
npm start
# Select: sample-code.js
# Test each command: fix, optimize, explain, refactor
```

2. **Test error handling:**
```bash
# Remove/corrupt .env and test validation
# Try invalid file types
# Test with files > 1MB
```

3. **Test file operations:**
```bash
# Create files with special characters
# Test file backup creation
# Test overwriting files
```

### Adding Tests (Future Enhancement)

```javascript
// tests/utils.test.js
import { normalizeCommand, isValidFileType } from "../utils.js";

describe("normalizeCommand", () => {
  it("should normalize fix aliases", () => {
    assert.equal(normalizeCommand("debug"), "fix");
    assert.equal(normalizeCommand("bug"), "fix");
  });
});

describe("isValidFileType", () => {
  it("should accept JavaScript files", () => {
    assert.equal(isValidFileType("app.js"), true);
  });

  it("should reject binary files", () => {
    assert.equal(isValidFileType("image.png"), false);
  });
});
```

## Performance Optimizations

### Current Approach
- Stream large files for display (first 50 lines)
- Full content sent to API (up to 1MB limit)
- Caching could be added for repeat analyses

### Future Improvements
1. **Caching:** Store analysis results for identical code
2. **Parallel Processing:** Analyze multiple files simultaneously
3. **Streaming:** Stream API responses for faster display
4. **Incremental Updates:** Show results as they arrive

## Security Considerations

✅ **Current Security:**
- API key stored only in `.env`
- No credentials logged
- File size limits prevent DOS
- Input validation on all user inputs

⚠️ **Future Considerations:**
- Rate limiting to prevent abuse
- API key rotation suggestions
- Audit logging for enterprise use
- Encryption of backup files

## Debugging

### Enable Verbose Logging

Add to `index.js`:
```javascript
const DEBUG = process.env.DEBUG === "true";

function debug(message) {
  if (DEBUG) console.log(`[DEBUG] ${message}`);
}
```

Run with:
```bash
DEBUG=true npm start
```

### Common Issues

**Issue: "gemini.js is not exported correctly"**
- Check `index.js` imports match function names
- Verify `export` statements in all modules

**Issue: "prompts library not working"**
- Verify prompt object has required `name` field
- Check field types match expected input types

**Issue: "File operations timing out"**
- Add timeout to fs.promises operations
- Check disk I/O performance

## Building for Production

### Code Quality Checklist
- [ ] All functions have JSDoc comments
- [ ] Error messages are user-friendly
- [ ] No hardcoded credentials
- [ ] File operations use absolute paths
- [ ] All async operations use try-catch
- [ ] Tested with various file sizes
- [ ] Tested error scenarios

### Before Release
```bash
# Clean dependencies
npm ci

# Check for security issues
npm audit

# List file structure
ls -la

# Test complete flow
npm start
```

### Versioning
- Use semantic versioning: `MAJOR.MINOR.PATCH`
- Update `package.json` version before release
- Tag releases in git: `git tag v1.0.0`

## Contributing Guidelines

1. **Fork & Create Branch**
```bash
git checkout -b feature/new-command
```

2. **Code Changes**
- Follow code standards above
- Add JSDoc comments
- Include error handling
- Test thoroughly

3. **Commit with Clear Messages**
```bash
git commit -m "feat: add test generation command"
```

4. **Push & Create Pull Request**
```bash
git push origin feature/new-command
```

## Useful Commands

```bash
# Install/update dependencies
npm install
npm update

# Check for outdated packages
npm outdated

# Audit security
npm audit
npm audit fix

# Clean install
npm ci

# Run the app
npm start

# Check Node version
node --version
```

## Resources

- [Google Generative AI Docs](https://ai.google.dev)
- [Node.js Best Practices](https://nodejs.org/en/docs/guides/)
- [JavaScript async/await](https://javascript.info/async-await)
- [npm Documentation](https://docs.npmjs.com/)

## Future Roadmap

- [ ] Multi-file batch analysis
- [ ] Analysis history & reports
- [ ] Custom prompt templates
- [ ] VS Code extension
- [ ] Web UI interface
- [ ] Unit test generation
- [ ] Documentation generation
- [ ] Git integration
- [ ] Performance profiling
- [ ] Database optimization suggestions

## Questions?

- Check README.md for usage documentation
- Review QUICKSTART.md for common tasks
- Read code comments for implementation details
- Check error messages for troubleshooting

---

**Happy coding!** 🚀
