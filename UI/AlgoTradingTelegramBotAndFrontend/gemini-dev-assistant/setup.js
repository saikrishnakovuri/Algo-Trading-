#!/usr/bin/env node

/**
 * Setup Script for Gemini Dev Assistant
 * Automates initial configuration and validation
 * 
 * Usage: node setup.js
 */

import fs from "fs";
import path from "path";
import readline from "readline";

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function question(query) {
  return new Promise(resolve => rl.question(query, resolve));
}

async function runSetup() {
  console.clear();
  console.log("╔═══════════════════════════════════════════════╗");
  console.log("║     🤖 Gemini Dev Assistant Setup Wizard      ║");
  console.log("╚═══════════════════════════════════════════════╝\n");

  try {
    // Step 1: Check Node.js version
    console.log("📋 Checking environment...");
    const nodeVersion = process.version;
    const majorVersion = parseInt(nodeVersion.slice(1).split(".")[0]);

    if (majorVersion < 18) {
      console.error(
        `❌ Node.js 18+ required (you have ${nodeVersion})\n` +
        "   Download from: https://nodejs.org/"
      );
      process.exit(1);
    }
    console.log(`✅ Node.js ${nodeVersion}`);

    // Step 2: Check if node_modules exists
    if (!fs.existsSync("node_modules")) {
      console.log("\n📦 Installing dependencies...");
      console.log("   Run: npm install\n");
      process.exit(0);
    }
    console.log("✅ Dependencies installed");

    // Step 3: Check for .env file
    console.log("\n🔑 Checking configuration...");
    let envExists = fs.existsSync(".env");

    if (!envExists) {
      console.log("⚠️  .env file not found");

      // Create .env from template
      if (fs.existsSync(".env.example")) {
        const envContent = fs.readFileSync(".env.example", "utf-8");
        fs.writeFileSync(".env", envContent);
        console.log("✅ Created .env from template");
        envExists = true;
      }
    }

    if (!envExists) {
      console.log("❌ Cannot find .env file");
      process.exit(1);
    }

    // Step 4: Check API key
    const envContent = fs.readFileSync(".env", "utf-8");
    const apiKeyMatch = envContent.match(/GEMINI_API_KEY=(.+)/);
    const apiKey = apiKeyMatch ? apiKeyMatch[1].trim() : "";

    if (!apiKey || apiKey === "your_api_key_here") {
      console.log("⚠️  API key not configured");
      console.log("\n📖 Getting your API key:\n");
      console.log("   1. Visit: https://aistudio.google.com/app/apikeys");
      console.log("   2. Click 'Create API Key'");
      console.log("   3. Copy your key\n");

      const userApiKey = await question("   Paste your API key (or press Enter to skip): ");

      if (userApiKey && userApiKey !== "your_api_key_here") {
        const updatedEnv = envContent.replace(
          /GEMINI_API_KEY=.*/,
          `GEMINI_API_KEY=${userApiKey}`
        );
        fs.writeFileSync(".env", updatedEnv);
        console.log("✅ API key saved to .env");
      } else {
        console.log("⚠️  Skipped API key configuration");
        console.log("   You can add it later by editing .env\n");
      }
    } else {
      console.log("✅ API key configured");
    }

    // Step 5: Check for sample file
    console.log("\n📁 Checking sample files...");
    if (!fs.existsSync("sample-code.js")) {
      console.log("⚠️  sample-code.js not found");
    } else {
      console.log("✅ Sample code file available");
    }

    // Step 6: Validate setup
    console.log("\n✨ Validating setup...");

    const checks = {
      "package.json": fs.existsSync("package.json"),
      ".env": fs.existsSync(".env"),
      "index.js": fs.existsSync("index.js"),
      "gemini.js": fs.existsSync("gemini.js"),
      "fileReader.js": fs.existsSync("fileReader.js"),
      "utils.js": fs.existsSync("utils.js")
    };

    let allGood = true;
    for (const [file, exists] of Object.entries(checks)) {
      console.log(exists ? `  ✅ ${file}` : `  ❌ ${file}`);
      if (!exists) allGood = false;
    }

    if (!allGood) {
      console.error("\n❌ Some files are missing!");
      process.exit(1);
    }

    // Final message
    console.log("\n╔═══════════════════════════════════════════════╗");
    console.log("║         ✅ Setup Complete!                   ║");
    console.log("╚═══════════════════════════════════════════════╝\n");

    console.log("🚀 Ready to use! Start with:\n");
    console.log("   npm start\n");

    console.log("📖 For help, read:\n");
    console.log("   • QUICKSTART.md - Get started in 5 minutes");
    console.log("   • README.md - Full documentation");
    console.log("   • DEVELOPMENT.md - For contributors\n");

    console.log("💡 First time? Try this:\n");
    console.log("   1. npm start");
    console.log("   2. Type: fix");
    console.log("   3. Select: sample-code.js");
    console.log("   4. Press Enter to analyze\n");

    process.exit(0);
  } catch (error) {
    console.error(`\n❌ Setup error: ${error.message}`);
    process.exit(1);
  } finally {
    rl.close();
  }
}

// Run setup
runSetup();
