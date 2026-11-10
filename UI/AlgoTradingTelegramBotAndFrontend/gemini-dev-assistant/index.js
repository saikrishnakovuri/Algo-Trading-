/**
 * Gemini Dev Assistant - Main CLI Interface
 * A local developer assistant integrated with Google Gemini API
 * 
 * Usage: node index.js
 * 
 * Commands:
 *   fix - Find and fix bugs in code
 *   optimize - Optimize code for performance
 *   explain - Get detailed explanation of code
 *   refactor - Improve code structure and quality
 *   exit - Exit the program
 */

import dotenv from "dotenv";
import prompts from "prompts";
import {
  initializeGemini,
  analyzeWithCommand,
  isGeminiInitialized
} from "./gemini.js";
import {
  listFiles,
  readFile,
  writeFile,
  createBackup,
  getFileInfo
} from "./fileReader.js";
import {
  validateApiKey,
  normalizeCommand,
  formatFileContent,
  truncatePrompt
} from "./utils.js";

// Load environment variables
dotenv.config();

// Constants
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;
const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-1.5-pro";
const COMMANDS = ["fix", "optimize", "explain", "refactor"];

// Global state
let isRunning = true;

/**
 * Displays the welcome banner
 */
function displayBanner() {
  console.clear();
  console.log("╔═══════════════════════════════════════════════╗");
  console.log("║       🤖 Gemini Dev Assistant v1.0.0         ║");
  console.log("║     Powered by Google Generative AI          ║");
  console.log("╚═══════════════════════════════════════════════╝");
  console.log("");
}

/**
 * Displays available commands
 */
function displayCommands() {
  console.log("\n📋 Available Commands:");
  console.log("  • fix      - Find and fix bugs in code");
  console.log("  • optimize - Optimize code for performance");
  console.log("  • explain  - Get detailed explanation of code");
  console.log("  • refactor - Improve code structure and quality");
  console.log("  • exit     - Exit the program\n");
}

/**
 * Main interactive loop
 */
async function mainLoop() {
  displayBanner();

  // Validate API key
  try {
    validateApiKey(GEMINI_API_KEY);
    console.log("✅ API Key validated");
  } catch (error) {
    console.error(error.message);
    process.exit(1);
  }

  // Initialize Gemini API
  try {
    initializeGemini(GEMINI_API_KEY, GEMINI_MODEL);
  } catch (error) {
    console.error(`❌ Failed to initialize Gemini: ${error.message}`);
    process.exit(1);
  }

  displayCommands();

  while (isRunning) {
    try {
      // Step 1: Get command from user
      const { command } = await prompts({
        type: "text",
        name: "command",
        message: "Enter command (fix/optimize/explain/refactor/exit)",
        validate: value => {
          const normalized = normalizeCommand(value);
          return COMMANDS.includes(normalized) || value.toLowerCase() === "exit"
            ? true
            : "Invalid command. Try: fix, optimize, explain, refactor, or exit";
        }
      });

      const normalizedCommand = command.toLowerCase().trim();

      // Handle exit
      if (normalizedCommand === "exit") {
        console.log("\n👋 Goodbye!");
        isRunning = false;
        break;
      }

      // Step 2: List available files
      let files;
      try {
        files = await listFiles(".");
      } catch (error) {
        console.error(`❌ ${error.message}`);
        continue;
      }

      if (files.length === 0) {
        console.log(
          "\n⚠️  No code files found in current directory. " +
          "Create some code files and try again."
        );
        continue;
      }

      console.log(`\n📁 Found ${files.length} code files:\n`);
      files.forEach((file, index) => {
        console.log(`  ${index + 1}. ${file.name}`);
      });

      // Step 3: Select file
      const { fileIndex } = await prompts({
        type: "number",
        name: "fileIndex",
        message: "Select file number (or -1 to cancel)",
        validate: value => {
          if (value === -1) return true;
          return value >= 1 && value <= files.length
            ? true
            : `Please enter a number between 1 and ${files.length}`;
        }
      });

      if (fileIndex === -1) {
        console.log("Cancelled.\n");
        continue;
      }

      const selectedFile = files[fileIndex - 1];

      // Step 4: Read file and get file info
      let fileContent;
      let fileInfo;
      try {
        fileContent = await readFile(selectedFile.path);
        fileInfo = await getFileInfo(selectedFile.path);
      } catch (error) {
        console.error(`❌ ${error.message}`);
        continue;
      }

      console.log(`\n📄 File: ${fileInfo.name} (${fileInfo.sizeFormatted})`);
      console.log(`${fileInfo.name}:`);
      console.log("─".repeat(50));
      console.log(formatFileContent(fileContent, 30));
      console.log("─".repeat(50));

      // Step 5: Get additional context from user
      const { userContext } = await prompts({
        type: "text",
        name: "userContext",
        message: "Additional context or specific instructions (optional)",
        initial: ""
      });

      // Step 6: Send to Gemini and get analysis
      let analysis;
      try {
        console.log("\n🔄 Analyzing code...");
        analysis = await analyzeWithCommand(
          fileContent,
          normalizeCommand(normalizedCommand),
          selectedFile.name,
          userContext
        );
      } catch (error) {
        console.error(`\n❌ ${error.message}`);
        continue;
      }

      // Step 7: Display analysis result
      console.log("\n" + "=".repeat(60));
      console.log(`✅ ${normalizeCommand(normalizedCommand).toUpperCase()} Analysis`);
      console.log("=".repeat(60));
      console.log(analysis);
      console.log("=".repeat(60) + "\n");

      // Step 8: For fix/refactor/optimize, offer to save changes
      if (["fix", "optimize", "refactor"].includes(normalizeCommand(normalizedCommand))) {
        const { wantsSave } = await prompts({
          type: "confirm",
          name: "wantsSave",
          message: "Would you like to save these changes to the file?",
          initial: false
        });

        if (wantsSave) {
          try {
            // Extract code from response (assuming it's wrapped in code blocks)
            let codeToSave = analysis;

            // Try to extract code from markdown code blocks
            const codeBlockMatch = analysis.match(/```[\w]*\n([\s\S]*?)\n```/);
            if (codeBlockMatch) {
              codeToSave = codeBlockMatch[1];
            }

            // Create backup
            const backupPath = await createBackup(selectedFile.path);
            console.log(`\n📦 Backup created: ${backupPath}`);

            // Write new content
            await writeFile(selectedFile.path, codeToSave);
            console.log(`✅ File saved: ${selectedFile.name}`);
          } catch (error) {
            console.error(`❌ Failed to save file: ${error.message}`);
          }
        }
      }

      // Ask if user wants to continue
      const { continueCLI } = await prompts({
        type: "confirm",
        name: "continueCLI",
        message: "Analyze another file?",
        initial: true
      });

      if (!continueCLI) {
        console.log("\n👋 Goodbye!");
        isRunning = false;
      }
    } catch (error) {
      if (error.message === "User force closed the prompt") {
        console.log("\n👋 Goodbye!");
        isRunning = false;
      } else {
        console.error(`\n❌ Error: ${error.message}`);
      }
    }
  }

  process.exit(0);
}

/**
 * Handle graceful shutdown
 */
process.on("SIGINT", () => {
  console.log("\n\n👋 Goodbye!");
  process.exit(0);
});

// Start the CLI
mainLoop().catch(error => {
  console.error(`❌ Fatal error: ${error.message}`);
  process.exit(1);
});
