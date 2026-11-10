/*
 * VS Code Extension: Gemini Code Assistant
 * - Registers commands: explain, fix, optimize, refactor
 * - Sends selected code to Gemini via geminiService
 * - Shows results in a Webview panel with optional "Apply" button
 */

const vscode = require('vscode');
const gemini = require('./geminiService');

/**
 * Activate the extension
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  console.log('Gemini Code Assistant activated');

  const commands = ['explain', 'fix', 'optimize', 'refactor'];

  commands.forEach((cmd) => {
    const disposable = vscode.commands.registerCommand(`gemini.${cmd}`, async () => {
      try {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
          vscode.window.showInformationMessage('Open a file and select some code to analyze.');
          return;
        }

        const selection = editor.selection;
        const selectedText = editor.document.getText(selection).trim();
        if (!selectedText) {
          vscode.window.showInformationMessage('Please select code first.');
          return;
        }

        // Read API configuration from settings or environment
        const config = vscode.workspace.getConfiguration('gemini');
        const apiKey = config.get('apiKey') || process.env.GEMINI_API_KEY;
        const model = config.get('model') || 'gemini-1.5-pro-latest';

        if (!apiKey) {
          vscode.window.showErrorMessage(
            'Gemini API key not configured. Set `gemini.apiKey` in Settings or set GEMINI_API_KEY environment variable.'
          );
          return;
        }

        // Initialize Gemini service (safe to call multiple times)
        await gemini.initialize(apiKey, model);

        const fileName = editor.document.fileName || '';

        await vscode.window.withProgress(
          {
            location: vscode.ProgressLocation.Notification,
            title: `Gemini: ${cmd}`,
            cancellable: false
          },
          async (progress) => {
            progress.report({ message: 'Sending selection to Gemini...' });
            const result = await gemini.analyzeWithCommand(selectedText, cmd, fileName);
            showResultWebview(context, cmd, selectedText, result, editor, selection);
          }
        );
      } catch (err) {
        vscode.window.showErrorMessage(`Gemini Error: ${err.message || String(err)}`);
        console.error(err);
      }
    });

    context.subscriptions.push(disposable);
  });
}

/**
 * Show the Gemini response in a Webview panel with optional Apply button.
 * If the user clicks Apply, the selection is replaced with the panel content.
 */
function showResultWebview(context, command, originalText, resultText, editor, selection) {
  const panel = vscode.window.createWebviewPanel('geminiResult', `Gemini: ${command}`, vscode.ViewColumn.Beside, {
    enableScripts: true
  });

  const safeHtml = escapeHtml(resultText);
  const canApply = ['fix', 'refactor', 'optimize'].includes(command);
  const applyButtonHtml = canApply ? '<button id="apply">Apply Changes</button>' : '';

  panel.webview.html = `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';">
  <style>
    body { font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial; padding: 12px; }
    pre { background:#1e1e1e; color:#d4d4d4; padding:12px; white-space:pre-wrap; overflow:auto; }
    button { margin-top:8px; padding:6px 10px; }
  </style>
</head>
<body>
  <h2>Gemini: ${escapeHtml(command)}</h2>
  <div>
    <pre id="result">${safeHtml}</pre>
    ${applyButtonHtml}
  </div>
  <script>
    const vscode = acquireVsCodeApi();
    const apply = document.getElementById('apply');
    if (apply) {
      apply.addEventListener('click', () => {
        const code = document.getElementById('result').innerText;
        vscode.postMessage({ command: 'apply', code });
      });
    }
  </script>
</body>
</html>`;

  // Handle messages from the webview
  panel.webview.onDidReceiveMessage(
    (message) => {
      if (message.command === 'apply') {
        const code = message.code;
        editor.edit((editBuilder) => {
          editBuilder.replace(selection, code);
        }).then(
          (ok) => {
            if (ok) {
              vscode.window.showInformationMessage('Selection replaced with Gemini suggestion.');
              panel.dispose();
            } else {
              vscode.window.showErrorMessage('Failed to apply changes to the editor.');
            }
          },
          (err) => {
            vscode.window.showErrorMessage('Failed to apply changes: ' + err.message);
          }
        );
      }
    },
    undefined,
    context.subscriptions
  );
}

/**
 * Simple HTML escape for embedding results
 */
function escapeHtml(unsafe) {
  if (!unsafe) return '';
  return String(unsafe)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function deactivate() {
  // Cleanup if needed
}

module.exports = { activate, deactivate };
