/**
 * Sample Code File for Testing Gemini Dev Assistant
 * 
 * This file contains intentional bugs and areas for improvement
 * Use this to test the "fix", "optimize", "explain", and "refactor" commands
 */

// ❌ BUG: Not handling null/undefined cases
function calculateTotal(items) {
  let total = 0;
  for (let i = 0; i < items.length; i++) {
    total = total + items[i].price * items[i].quantity;
  }
  return total;
}

// ❌ BUG: Missing error handling
function fetchUserData(userId) {
  const response = fetch(`/api/users/${userId}`);
  const data = response.json();
  return data;
}

// ❌ PERFORMANCE: Inefficient nested loops
function findDuplicates(array1, array2) {
  const duplicates = [];
  for (let i = 0; i < array1.length; i++) {
    for (let j = 0; j < array2.length; j++) {
      if (array1[i] === array2[j]) {
        duplicates.push(array1[i]);
      }
    }
  }
  return duplicates;
}

// ❌ READABILITY: Complex nested conditionals
function validateUser(user) {
  if (user.age >= 18) {
    if (user.email && user.email.includes("@")) {
      if (user.name && user.name.length > 0) {
        if (user.password && user.password.length >= 8) {
          return true;
        }
      }
    }
  }
  return false;
}

// ❌ MEMORY: Not freeing resources
function processLargeFile(filePath) {
  const fs = require("fs");
  const data = fs.readFileSync(filePath, "utf-8");
  const lines = data.split("\n");
  // Processing...
  return lines.map(line => line.toUpperCase());
}

// ❌ SECURITY: Password in plain text
function login(username, password) {
  const users = {
    admin: "admin123",
    user: "password456"
  };

  if (users[username] === password) {
    return true;
  }
  return false;
}

// ❌ ASYNC: Missing await
async function loadMultipleUsers(userIds) {
  const users = [];
  for (const id of userIds) {
    const user = fetchUserData(id); // Missing await!
    users.push(user);
  }
  return users;
}

// ✅ Example of good code (for reference)
function greetUser(name) {
  if (!name || typeof name !== "string") {
    throw new Error("Name must be a non-empty string");
  }
  return `Hello, ${name}!`;
}

module.exports = {
  calculateTotal,
  fetchUserData,
  findDuplicates,
  validateUser,
  processLargeFile,
  login,
  loadMultipleUsers,
  greetUser
};
