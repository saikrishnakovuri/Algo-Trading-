import fs from 'fs';
import path from 'path';
import { validateApiKey, isValidFileType, formatFileContent } from './utils.js';
import { listFiles, readFile } from './fileReader.js';
import * as geminiModule from './gemini.js';

async function runSmoke() {
  console.log('== Smoke Test: Gemini Dev Assistant ==');

  const apiKey = process.env.GEMINI_API_KEY || 'test_api_key';
  try {
    validateApiKey(apiKey);
    console.log('✓ validateApiKey passed');
  } catch (err) {
    console.warn('! validateApiKey warning:', err.message);
  }

  // List files in current folder
  try {
    const files = await listFiles('.');
    console.log(`✓ listFiles found ${files.length} entries`);
    if (files.length > 0) {
      console.log('  sample:', files.slice(0, 5).map(f => f.name).join(', '));
    }
  } catch (err) {
    console.error('✗ listFiles failed:', err.message);
  }

  // Read this file (fileReader)
  try {
    const content = await readFile('./fileReader.js');
    console.log('✓ readFile(fileReader.js) length:', content.length);
    console.log('  preview:\n', formatFileContent(content, 6));
  } catch (err) {
    console.error('✗ readFile failed:', err.message);
  }

  // Validate helper
  console.log('✓ isValidFileType tests:', ['index.js', 'README.md', 'binary.bin'].map(n => `${n}:${isValidFileType(n)}`).join(' | '));

  // Check gemini module functions (no network calls)
  try {
    console.log('✓ gemini.isGeminiInitialized():', geminiModule.isGeminiInitialized());
    console.log('✓ gemini.getAvailableModels():', geminiModule.getAvailableModels().slice(0,3).join(', '));
  } catch (err) {
    console.error('✗ gemini module check failed:', err.message);
  }

  // Check VS Code extension files and node_modules existence
  const extDir = path.join('.', 'vscode-extension');
  const extFiles = ['extension.js', 'geminiService.js', 'package.json'];
  extFiles.forEach(f => {
    const p = path.join(extDir, f);
    console.log(`${p}: ${fs.existsSync(p) ? 'exists' : 'missing'}`);
  });
  
  const extNodeModules = path.join(extDir, 'node_modules');
  console.log(`${extNodeModules}: ${fs.existsSync(extNodeModules) ? 'exists' : 'missing'}`);

  console.log('\n== Smoke test complete ==');
}

runSmoke().catch(err => {
  console.error('Smoke test error:', err);
  process.exit(1);
});
