const argon2 = require('argon2');

/**
 * Hash a plain text password using Argon2
 * @param {string} password
 * @returns {Promise<string>}
 */
const hashPassword = async (password) => {
  return await argon2.hash(password);
};

/**
 * Verify a password against a hash
 * @param {string} hash
 * @param {string} password
 * @returns {Promise<boolean>}
 */
const verifyPassword = async (hash, password) => {
  try {
    return await argon2.verify(hash, password);
  } catch (err) {
    return false;
  }
};

module.exports = {
  hashPassword,
  verifyPassword
};
