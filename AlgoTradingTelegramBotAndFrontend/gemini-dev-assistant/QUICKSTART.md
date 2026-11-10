# 🚀 Quick Start Guide

Get up and running with Gemini Dev Assistant in 5 minutes!

## 1️⃣ Prerequisites

Ensure you have:
- **Node.js 18+** - Check with `node --version`
- **npm** - Usually comes with Node.js

## 2️⃣ Get Your API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikeys)
2. Click **"Create API Key"**
3. Select **"Create API key in new project"**
4. Copy the generated key (looks like: `AIzaSy...`)
5. Keep it safe - never share it!

## 3️⃣ Installation (3 commands)

```bash
# Navigate to project directory
cd gemini-dev-assistant

# Install dependencies
npm install

# Copy environment template
cp .env.example .env
```

## 4️⃣ Configure API Key

Open `.env` file and replace:
```
GEMINI_API_KEY=your_api_key_here
```

with your actual API key:
```
GEMINI_API_KEY=AIzaSyD1234567890abcdefghijklmnopqrstuvwxyz
```

## 5️⃣ Run the Assistant

```bash
npm start
```

You should see:
```
╔═══════════════════════════════════════════════╗
║       🤖 Gemini Dev Assistant v1.0.0         ║
║     Powered by Google Generative AI          ║
╚═══════════════════════════════════════════════╝

✅ API Key validated
✅ Gemini API initialized with model: gemini-1.5-pro

📋 Available Commands:
  • fix      - Find and fix bugs in code
  • optimize - Optimize code for performance
  • explain  - Get detailed explanation of code
  • refactor - Improve code structure and quality
  • exit     - Exit the program

Enter command (fix/optimize/explain/refactor/exit):
```

## 6️⃣ Try Your First Analysis

1. Type: `fix`
2. Select a code file from your directory
3. Press Enter (skip additional context for now)
4. Watch the AI analyze your code!

## Common Commands

| Command | Use Case |
|---------|----------|
| `fix` | Find bugs and issues |
| `optimize` | Improve performance |
| `explain` | Understand code logic |
| `refactor` | Improve code quality |
| `exit` | Quit program |

## File Formats Supported

Just put any code files in the directory:
- `.js`, `.ts`, `.jsx`, `.tsx` (JavaScript/TypeScript)
- `.py` (Python)
- `.java` (Java)
- `.cpp`, `.c`, `.h` (C/C++)
- `.cs` (C#)
- `.go`, `.rs`, `.php`, `.rb` (Other languages)
- `.json`, `.yaml`, `.xml`, `.sql` (Configs/Data)

## Troubleshooting

**Problem: "GEMINI_API_KEY is not configured"**
- ✅ Make sure .env file exists
- ✅ Copy from .env.example: `cp .env.example .env`
- ✅ Paste your real API key in .env

**Problem: "Invalid API key"**
- ✅ Check API key from Google AI Studio
- ✅ No extra spaces before/after
- ✅ Copy-paste exactly

**Problem: "No code files found"**
- ✅ Create a test file: `echo "console.log('test')" > test.js`
- ✅ Then run `npm start` again

**Problem: "File too large"**
- ✅ Files must be under 1MB
- ✅ This is an API limit

## Next Steps

- Read full [README.md](README.md) for advanced features
- Add custom context to get better analyses
- Explore all four commands on your code
- Check the [troubleshooting guide](README.md#troubleshooting) if stuck

## File Structure

```
gemini-dev-assistant/
├── index.js         ← Main CLI app
├── gemini.js        ← AI integration
├── fileReader.js    ← File operations
├── utils.js         ← Helper functions
├── .env             ← Your config (create from .env.example)
├── .env.example     ← Config template
├── package.json     ← Dependencies
└── README.md        ← Full documentation
```

## Tips for Best Results

1. **Be specific** - Add context: "Focus on security" or "Optimize database queries"
2. **Smaller chunks** - Analyze 1-2 functions at a time for better insights
3. **Read backups** - When you save changes, backups are created automatically
4. **Use Flash model** - Faster/cheaper: set `GEMINI_MODEL=gemini-1.5-flash` in .env

## Rate Limits

Free tier includes:
- ✅ 60 requests per minute
- ✅ 1 million tokens per day
- ✅ Full model access

Plenty for learning and development!

## Security Reminders

🔐 **Important:**
- Never commit `.env` file to git
- Never share your API key
- Check `.gitignore` includes `.env`
- Rotate keys periodically in Google AI Studio

---

Ready to go! 🎉 Run `npm start` and analyze your first code!
