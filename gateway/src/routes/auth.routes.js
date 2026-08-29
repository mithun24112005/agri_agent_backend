const express = require('express');
const { z } = require('zod');
const { validateRequest } = require('../middleware/validation.middleware');
const { requireAuth } = require('../middleware/auth.middleware');
const { requireRedis, registerLimiter, loginLimiter } = require('../middleware/rateLimit.middleware');
const authController = require('../controllers/auth.controller');

const router = express.Router();

const registerSchema = {
  body: z.object({
    email: z.string().email('Invalid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters long')
  })
};

const loginSchema = {
  body: z.object({
    email: z.string().email('Invalid email address'),
    password: z.string().min(1, 'Password is required')
  })
};

const refreshSchema = {
  body: z.object({
    refreshToken: z.string().min(1, 'Refresh token is required')
  })
};

// Fail-safe Redis check for Auth endpoints + Rate limiting
router.post('/register', requireRedis, registerLimiter, validateRequest(registerSchema), authController.register);
router.post('/login', requireRedis, loginLimiter, validateRequest(loginSchema), authController.login);
router.post('/refresh', validateRequest(refreshSchema), authController.refresh);
router.post('/logout', requireAuth, authController.logout);
router.get('/me', requireAuth, authController.getMe);

module.exports = router;
