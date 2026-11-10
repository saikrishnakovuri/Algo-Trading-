# 🤖 Gemini Dev Assistant

A powerful, production-ready local developer assistant that integrates Google Gemini API into a CLI-based coding agent. Analyze, fix, optimize, explain, and refactor your code directly from the terminal.

## Features

✨ **Core Features:**
- 🔧 **Fix Bugs** - Identify and fix bugs in your code
- ⚡ **Optimize** - Improve performance, memory usage, and efficiency
- 📚 **Explain** - Get detailed explanations of code logic
- 🔄 **Refactor** - Improve code structure and maintainability
- 📁 **File Management** - Seamlessly read/write code files
- 💾 **Automatic Backups** - Creates backups before saving changes
- 🛡️ **Error Handling** - Comprehensive error handling and validation
- 📝 **Interactive CLI** - User-friendly terminal interface

## Prerequisites

- **Node.js** 18.0.0 or higher
- **npm** or yarn
- **Google Generative AI API Key** (free tier available)

## Installation

### 1. Clone or Navigate to Project

```bash
cd gemini-dev-assistant
```

### 2. Install Dependencies

```bash
npm install
```

This installs:
- `@google/generative-ai` - Official Google Gemini SDK
- `dotenv` - Environment variable management
- `prompts` - Interactive CLI prompts

### 3. Get Your Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikeys)
2. Click "Create API Key"
3. Select "Create API key in new project" or existing project
4. Copy the API key

### 4. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and paste your API key
# Open .env in your editor and set:
# GEMINI_API_KEY=your_actual_key_here
# GEMINI_MODEL=gemini-1.5-pro
```

**Example .env file:**
```
GEMINI_API_KEY=AIzaSyD1234567890abcdefghijklmnopqrstuvwxyz
GEMINI_MODEL=gemini-1.5-pro
```

## Usage

### Starting the Assistant

```bash
npm start
```

or

```bash
node index.js
```

### Interactive Workflow

1. **Choose a command:**
   - `fix` - Fix bugs
   - `optimize` - Optimize code
   - `explain` - Understand code
   - `refactor` - Improve code quality
   - `exit` - Quit

2. **Select a file:**
   - The assistant lists all supported code files in the current directory
   - Choose by entering the file number

3. **Optional: Add context:**
   - Provide additional instructions or specific requirements
   - Leave empty if not needed

4. **Review analysis:**
   - The assistant displays the analysis result
   - For fix/optimize/refactor: optionally save changes

5. **Automatic backup:**
   - If you save changes, a backup is created
   - Backup format: `filename.backup.{timestamp}`

## Supported File Types

The assistant supports analysis for:

**Programming Languages:**
- JavaScript/TypeScript (`.js`, `.jsx`, `.ts`, `.tsx`)
- Python (`.py`)
- Java (`.java`)
- C/C++ (`.cpp`, `.c`, `.h`)
- C# (`.cs`)
- PHP (`.php`)
- Ruby (`.rb`)
- Go (`.go`)
- Rust (`.rs`)
- Kotlin (`.kt`)
- Swift (`.swift`)
- And many more...

**Web Technologies:**
- HTML (`.html`)
- CSS (`.css`, `.scss`, `.sass`, `.less`)
- Vue (`.vue`)

**Config & Data:**
- JSON (`.json`)
- XML (`.xml`)
- YAML (`.yaml`, `.yml`)
- TOML (`.toml`)
- SQL (`.sql`)

## Project Structure

```
gemini-dev-assistant/
├── index.js           # Main CLI interface and interactive loop
├── gemini.js          # Gemini API handler and integration
├── fileReader.js      # File I/O operations
├── utils.js           # Utility functions and validators
├── package.json       # Project dependencies
├── .env.example       # Example environment configuration
├── .env               # Actual environment config (create from .env.example)
└── README.md          # This file
```

### File Responsibilities

**index.js** (520+ lines)
- Interactive CLI menu and user prompts
- File selection interface
- Command processing and validation
- Integration of all modules
- User interaction flow management

**gemini.js** (180+ lines)
- Google Generative AI client initialization
- `analyzeCode()` - Send code to Gemini with context
- `analyzeWithCommand()` - Execute specific commands
- API error handling
- Model management

**fileReader.js** (200+ lines)
- `listFiles()` - List supported code files
- `readFile()` - Read file content with validation
- `writeFile()` - Write changes to file
- `createBackup()` - Create timestamped backups
- `getFileInfo()` - Get file metadata

**utils.js** (250+ lines)
- `validateApiKey()` - Validate API key configuration
- `isValidFileType()` - Check if file is supported
- `formatFileContent()` - Format code with line numbers
- `normalizeCommand()` - Handle command variations
- `handleApiError()` - User-friendly error messages
- System prompts for each command

## Examples

### Example 1: Fix a Bug

```
$ npm start

Enter command: fix
📁 Found 3 code files:
  1. app.js
  2. utils.js
  3. config.js

Select file number: 1
📄 File: app.js (2.5 KB)

Additional context: [leave empty or add instructions]

🔄 Analyzing code...

✅ FIX Analysis
=========================================================
I found the following bugs in your code:

1. **Missing null check** - Line 15
   The `data.user` might be undefined. Add: if (data?.user)

2. **Incorrect array access** - Line 23
   Using array index [0] directly without checking length

3. **Async/await issue** - Line 31
   Missing 'await' keyword before async function

Here's the corrected code:
```js
// ... [corrected code with fixes]
```
=========================================================

Would you like to save these changes? (Y/n): y
📦 Backup created: app.js.backup.1682425896123
✅ File saved: app.js
```

### Example 2: Optimize Performance

```
Enter command: optimize

[Select file...]

Additional context: Focus on database queries

🔄 Analyzing code...

✅ OPTIMIZE Analysis
=========================================================
I've identified performance improvements:

1. **Add database indexing** - Current query scans all records
   Suggested: Add index on 'userId' column

2. **Implement caching** - Users API is called multiple times
   Suggested: Use Redis cache with 5-min TTL

3. **Batch processing** - Process items one by one
   Suggested: Use Promise.all() for parallel execution

Optimized code:
```js
// ... [optimized version with improvements]
```
=========================================================
```

### Example 3: Explain Code

```
Enter command: explain

[Select file...]

🔄 Analyzing code...

✅ EXPLAIN Analysis
=========================================================
**Overview:**
This file implements a REST API middleware for authentication.

**Key Components:**

1. **Authentication Middleware** (Line 1-20)
   - Intercepts incoming requests
   - Validates JWT token from headers
   - Attaches user info to request object

2. **Token Verification** (Line 22-45)
   - Decodes JWT using secret key
   - Checks token expiration
   - Handles token refresh logic

3. **Error Handling** (Line 47-60)
   - Returns 401 for invalid tokens
   - Returns 403 for expired tokens

**Flow:**
Request → Check header → Decode JWT → Verify signature → Attach user → Next middleware

**Security Notes:**
- Token stored in httpOnly cookie (good practice)
- Secret key should be in environment variables (✓ already done)
=========================================================
```

## Error Handling

The assistant handles common errors gracefully:

| Error | Handling |
|-------|----------|
| Invalid API Key | Shows setup instructions |
| Rate Limited (429) | Informs to wait and retry |
| File Not Found | Lists available files |
| File Too Large (>1MB) | Skips the file |
| Empty Response | Displays error with retry option |
| Network Issues | Shows API error and suggests retry |
| Model Not Found | Lists available models |

## Advanced Usage

### Using Different Models

Edit `.env`:
```
GEMINI_MODEL=gemini-1.5-flash  # Faster, cheaper
# or
GEMINI_MODEL=gemini-1.5-pro    # More powerful
```

### Analyzing Specific Code Patterns

Add context when analyzing:
- "Focus on security vulnerabilities"
- "Look for memory leaks"
- "Check for race conditions"
- "Improve accessibility"

### Batch Processing

```bash
# Analyze multiple files by running the script multiple times
npm start  # First file
# [select and analyze file]
# [continue analyzing]
npm start  # Continue with another file
```

## Environment Variables

**Required:**
- `GEMINI_API_KEY` - Your Google Gemini API key

**Optional:**
- `GEMINI_MODEL` - Model to use (default: `gemini-1.5-pro`)

## Troubleshooting

### "GEMINI_API_KEY is not configured"
- Create `.env` file from `.env.example`
- Add your actual API key
- Restart the application

### "Invalid API key"
- Verify key from [Google AI Studio](https://aistudio.google.com/app/apikeys)
- Check for extra spaces or incorrect copy-paste
- Ensure API is enabled in Google Cloud project

### "No code files found"
- Create some code files in the directory
- Supported formats: `.js`, `.py`, `.java`, `.ts`, etc.

### "Rate limit reached"
- Wait a moment and try again
- Use `gemini-1.5-flash` for more requests
- Check your API quota at Google AI Studio

### File Not Saving
- Check file permissions
- Ensure disk has enough space
- Look for backup files (starting with `.backup.`)

## API Limits

**Free Tier:**
- 60 requests per minute
- 1 million tokens per day
- Models: gemini-1.5-pro, gemini-1.5-flash

**Paid Tier:**
- Higher limits based on plan
- More features available

## Performance Tips

1. **For large files:**
   - First 50 lines are shown for preview
   - Full content sent to Gemini (up to 1MB)

2. **For faster responses:**
   - Use `gemini-1.5-flash` for simple tasks
   - Use `gemini-1.5-pro` for complex analysis

3. **Optimize requests:**
   - Add specific context to get better results
   - Ask for specific improvements, not generic help

## Security Best Practices

✅ **Do:**
- Store API key in `.env` file (never in code)
- Use `.gitignore` to exclude `.env`
- Rotate API key regularly
- Use restricted API key with limited scopes

❌ **Don't:**
- Commit `.env` file to version control
- Share API key with others
- Use API key in frontend code
- Log API key in console output

## Development

### Project Architecture

```
┌─────────────┐
│   index.js  │  ← User Interface & CLI Loop
└─────┬───────┘
      │
      ├──> gemini.js      ← API Integration
      ├──> fileReader.js  ← File Operations
      └──> utils.js       ← Utilities & Validation
            │
            └──> Google Generative AI API
```

### Dependencies

```json
{
  "@google/generative-ai": "^0.21.0",  // Official Gemini SDK
  "dotenv": "^16.3.1",                  // Environment config
  "prompts": "^2.4.2"                   // Interactive CLI
}
```

### Code Quality

- ✅ Full JSDoc comments on all functions
- ✅ Error handling and validation
- ✅ Modular and testable code structure
- ✅ Configuration management
- ✅ User-friendly messages

## Limitations

- Maximum file size: 1 MB (API limit)
- Text-based files only (no binary)
- Rate limits apply based on tier
- Requires internet connection
- Response time depends on API availability

## Future Enhancements

- 🔄 Multi-file analysis
- 📊 Batch processing mode
- 🎯 Custom prompt templates
- 📈 Analysis history and reports
- 🔌 IDE plugin integration
- 🧪 Unit test generation
- 📝 Documentation generation
- ⚙️ Config file support

## Contributing

Feel free to extend this project:
- Add new analysis commands
- Improve error messages
- Add more file type support
- Optimize API usage

## License

MIT License - Feel free to use and modify

## Support

For issues or questions:
1. Check troubleshooting section
2. Review error messages
3. Verify API key and setup
4. Check Google Gemini API status

## References

- [Google Generative AI Docs](https://ai.google.dev)
- [Gemini API Reference](https://ai.google.dev/api)
- [Node.js Documentation](https://nodejs.org/docs/)

---

**Made with ❤️ using Google Gemini API**

Happy coding! 🚀
