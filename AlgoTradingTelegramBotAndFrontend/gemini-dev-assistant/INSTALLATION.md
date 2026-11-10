# 📦 Installation Guide

Complete installation instructions for all operating systems.

## Prerequisites

You need:
- **Node.js 18+**
- **npm** (comes with Node.js)
- **A text editor** (VS Code recommended)
- **Internet connection** (for API calls)

## Step-by-Step Installation

### Windows

**1. Install Node.js**
- Download from [nodejs.org](https://nodejs.org/)
- Choose "LTS" version
- Run installer, select defaults
- Restart computer

**2. Verify Installation**
```powershell
node --version
npm --version
```

Should show version numbers like `v20.0.0` and `9.0.0`

**3. Navigate to Project**
```powershell
cd C:\path\to\gemini-dev-assistant
```

**4. Install Dependencies**
```powershell
npm install
```

Wait 1-2 minutes for packages to download

**5. Get API Key**
- Visit https://aistudio.google.com/app/apikeys
- Click "Create API Key"
- Copy the key

**6. Configure API Key**
```powershell
# Copy template
copy .env.example .env

# Edit .env (open in Notepad or VS Code)
# Find: GEMINI_API_KEY=your_api_key_here
# Replace with your actual key
```

**7. Run Setup Validation**
```powershell
node setup.js
```

Follow prompts to validate setup

**8. Start Assistant**
```powershell
npm start
```

---

### macOS

**1. Install Node.js**

Using Homebrew (recommended):
```bash
brew install node@20
```

Or download from [nodejs.org](https://nodejs.org/)

**2. Verify Installation**
```bash
node --version
npm --version
```

**3. Navigate to Project**
```bash
cd /path/to/gemini-dev-assistant
```

**4. Install Dependencies**
```bash
npm install
```

**5. Get API Key**
- Visit https://aistudio.google.com/app/apikeys
- Click "Create API Key"
- Copy the key

**6. Configure API Key**
```bash
# Copy template
cp .env.example .env

# Edit .env (using your preferred editor)
nano .env
# or
code .env
```

Press `Ctrl+X`, then `Y`, then `Enter` to save in nano

**7. Run Setup Validation**
```bash
node setup.js
```

**8. Start Assistant**
```bash
npm start
```

---

### Linux (Ubuntu/Debian)

**1. Update Package Manager**
```bash
sudo apt update
```

**2. Install Node.js**
```bash
sudo apt install nodejs npm
```

Or for latest version:
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs
```

**3. Verify Installation**
```bash
node --version
npm --version
```

**4. Navigate to Project**
```bash
cd /path/to/gemini-dev-assistant
```

**5. Install Dependencies**
```bash
npm install
```

**6. Get API Key**
- Visit https://aistudio.google.com/app/apikeys
- Click "Create API Key"
- Copy the key

**7. Configure API Key**
```bash
# Copy template
cp .env.example .env

# Edit .env
nano .env
# or
code .env
```

**8. Run Setup Validation**
```bash
node setup.js
```

**9. Start Assistant**
```bash
npm start
```

---

### Docker (Optional)

If you prefer containerized setup:

**1. Build Docker Image**
```dockerfile
FROM node:20-alpine

WORKDIR /app
COPY . .
RUN npm install

ENV GEMINI_API_KEY=your_api_key_here

CMD ["npm", "start"]
```

**2. Build & Run**
```bash
docker build -t gemini-assistant .
docker run -it gemini-assistant
```

---

## Troubleshooting Installation

### ❌ "node: command not found"
- Node.js not installed or not in PATH
- Restart terminal/computer after installation
- Verify: `node --version`

### ❌ "npm ERR! code EACCES"
- Permission issue on macOS/Linux
- Solution: `sudo chown -R $(whoami) ~/.npm`

### ❌ "ENOENT: no such file or directory, open '.env'"
- .env file not created
- Run: `cp .env.example .env`

### ❌ "Module not found: @google/generative-ai"
- Dependencies not installed
- Run: `npm install`
- Wait for completion (don't interrupt)

### ❌ "Port already in use"
- Another app using port 8080 (if you extend this)
- Change port in configuration or kill other app

### ❌ "npm install takes forever"
- Check internet connection
- Try: `npm cache clean --force`
- Then: `npm install` again

---

## Verify Installation

Test that everything works:

**1. Check Files**
```bash
# Windows
dir

# macOS/Linux
ls -la
```

Should see: `index.js`, `gemini.js`, `fileReader.js`, `utils.js`, `package.json`, `.env`

**2. Run Setup Script**
```bash
node setup.js
```

Should show all ✅ marks

**3. Quick Test**
```bash
npm start
```

Should show welcome banner and wait for input

Press `Ctrl+C` to exit

---

## Next Steps

After successful installation:

1. **Read Quick Start**
   ```bash
   cat QUICKSTART.md
   ```

2. **Read Full Documentation**
   ```bash
   cat README.md
   ```

3. **Try Sample Analysis**
   ```bash
   npm start
   # Select: sample-code.js
   # Command: fix
   ```

4. **Run on Your Own Code**
   - Copy code files to the project directory
   - Run `npm start`
   - Select file and command

---

## Update Installation

To update to latest version:

```bash
# Pull latest code
git pull origin main

# Update dependencies
npm update

# Test
npm start
```

---

## Uninstall

To completely remove:

**Windows:**
```powershell
# Remove folder
Remove-Item -Path "C:\path\to\gemini-dev-assistant" -Recurse -Force

# Uninstall Node.js from Control Panel (optional)
```

**macOS:**
```bash
# Remove folder
rm -rf /path/to/gemini-dev-assistant

# Uninstall Node.js (if using Homebrew)
brew uninstall node
```

**Linux:**
```bash
# Remove folder
rm -rf /path/to/gemini-dev-assistant

# Uninstall Node.js
sudo apt remove nodejs npm
```

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Node.js | 18.0.0 | 20.0.0+ |
| npm | 9.0.0 | 10.0.0+ |
| RAM | 512 MB | 2 GB+ |
| Disk | 500 MB | 1 GB+ |
| OS | Any | Windows/macOS/Linux |

---

## Network Requirements

- ✅ Outbound HTTPS (port 443) to `generativelanguage.googleapis.com`
- ✅ Internet connection for API calls
- ✅ No firewall blocking Google APIs
- ✅ Free tier rate limits: 60 req/min, 1M tokens/day

---

## Getting Help

If installation fails:

1. **Check Node.js version** - Needs 18+
2. **Check npm version** - Needs 9+
3. **Check .env file** - Must have valid API key
4. **Read error message** - Usually gives solution
5. **Check firewall** - May block API calls
6. **Check internet** - API requires connection

For more help:
- Read QUICKSTART.md
- Check README.md troubleshooting
- Review DEVELOPMENT.md for code structure

---

## Success Indicators

✅ Installation is successful when:
- All files are present
- `npm install` completes without errors
- `node setup.js` shows all ✅ marks
- `npm start` shows welcome banner
- Can select files from directory

🎉 You're ready to analyze code with Gemini!
