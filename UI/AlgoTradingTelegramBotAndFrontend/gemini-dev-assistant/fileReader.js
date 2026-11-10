/**
 * File Reader and Writer Module
 * Handles reading, writing, and validating files
 */

import fs from "fs";
import path from "path";
import { isValidFileType } from "./utils.js";

/**
 * Lists all files in the current directory with text file extensions
 * @param {string} directory - Directory to scan (defaults to current directory)
 * @returns {Promise<Array>} Array of file objects with name and path
 */
export async function listFiles(directory = ".") {
  try {
    const files = await fs.promises.readdir(directory);
    const validFiles = files.filter(file => {
      // Skip node_modules, .git, hidden files, and non-text files
      if (
        file.startsWith(".") ||
        file === "node_modules" ||
        file === ".git" ||
        !isValidFileType(file)
      ) {
        return false;
      }
      return true;
    });

    return validFiles.map(file => ({
      name: file,
      path: path.join(directory, file)
    }));
  } catch (error) {
    throw new Error(`Failed to list files: ${error.message}`);
  }
}

/**
 * Reads file content from disk
 * @param {string} filePath - Path to the file
 * @returns {Promise<string>} File content
 */
export async function readFile(filePath) {
  try {
    // Resolve relative paths
    const absolutePath = path.resolve(filePath);

    // Check if file exists
    if (!fs.existsSync(absolutePath)) {
      throw new Error(`File not found: ${filePath}`);
    }

    // Check if it's a file (not directory)
    const stats = await fs.promises.stat(absolutePath);
    if (!stats.isFile()) {
      throw new Error(`Path is not a file: ${filePath}`);
    }

    // Check file size (limit to 1MB to avoid sending huge files)
    const maxSize = 1024 * 1024;
    if (stats.size > maxSize) {
      throw new Error(
        `File is too large (${(stats.size / 1024 / 1024).toFixed(2)}MB). Maximum is 1MB.`
      );
    }

    // Validate file type
    if (!isValidFileType(filePath)) {
      throw new Error(`Unsupported file type: ${path.extname(filePath)}`);
    }

    const content = await fs.promises.readFile(absolutePath, "utf-8");
    return content;
  } catch (error) {
    throw new Error(`Failed to read file: ${error.message}`);
  }
}

/**
 * Writes content to a file
 * @param {string} filePath - Path to the file
 * @param {string} content - Content to write
 * @returns {Promise<void>}
 */
export async function writeFile(filePath, content) {
  try {
    const absolutePath = path.resolve(filePath);

    // Ensure directory exists
    const dir = path.dirname(absolutePath);
    await fs.promises.mkdir(dir, { recursive: true });

    // Write file
    await fs.promises.writeFile(absolutePath, content, "utf-8");
  } catch (error) {
    throw new Error(`Failed to write file: ${error.message}`);
  }
}

/**
 * Creates a backup of the original file before overwriting
 * @param {string} filePath - Path to the file
 * @returns {Promise<string>} Path to the backup file
 */
export async function createBackup(filePath) {
  try {
    const absolutePath = path.resolve(filePath);
    const backupPath = `${absolutePath}.backup.${Date.now()}`;

    const content = await readFile(absolutePath);
    await writeFile(backupPath, content);

    return backupPath;
  } catch (error) {
    throw new Error(`Failed to create backup: ${error.message}`);
  }
}

/**
 * Gets file information (name, size, extension)
 * @param {string} filePath - Path to the file
 * @returns {Promise<Object>} File information
 */
export async function getFileInfo(filePath) {
  try {
    const absolutePath = path.resolve(filePath);

    if (!fs.existsSync(absolutePath)) {
      throw new Error(`File not found: ${filePath}`);
    }

    const stats = await fs.promises.stat(absolutePath);

    return {
      name: path.basename(absolutePath),
      path: absolutePath,
      extension: path.extname(absolutePath),
      size: stats.size,
      sizeFormatted: formatFileSize(stats.size),
      isFile: stats.isFile(),
      createdAt: stats.birthtime,
      modifiedAt: stats.mtime
    };
  } catch (error) {
    throw new Error(`Failed to get file info: ${error.message}`);
  }
}

/**
 * Formats file size to human-readable format
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size
 */
function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
}

export default {
  listFiles,
  readFile,
  writeFile,
  createBackup,
  getFileInfo
};
