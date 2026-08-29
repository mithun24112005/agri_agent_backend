const express = require('express');
const multer = require('multer');
const { requireAuth } = require('../middleware/auth.middleware');
const { requireRedis, chatLimiter, imageLimiter } = require('../middleware/rateLimit.middleware');
const chatController = require('../controllers/chat.controller');

const router = express.Router();

// Memory storage for multer - we'll just buffer it and send to FastAPI
const upload = multer({ 
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 5 * 1024 * 1024 // 5MB limit
  },
  fileFilter: (req, file, cb) => {
    // Basic type validation
    if (file.mimetype.startsWith('image/')) {
      cb(null, true);
    } else {
      cb(new Error('Only images are allowed'));
    }
  }
});

// Middleware to apply different limits if there's an image
const dynamicLimiter = (req, res, next) => {
  if (req.file) {
    return imageLimiter(req, res, next);
  }
  return chatLimiter(req, res, next);
};

// Error handling for Multer (e.g. file too large)
const multerErrorHandler = (err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    if (err.code === 'LIMIT_FILE_SIZE') {
      return res.status(413).json({ error: { code: 'PAYLOAD_TOO_LARGE', message: 'File is too large. Max size is 5MB.' } });
    }
    return res.status(400).json({ error: { code: 'BAD_REQUEST', message: err.message } });
  } else if (err) {
    return res.status(400).json({ error: { code: 'BAD_REQUEST', message: err.message } });
  }
  next();
};

// All chat routes require Auth
router.use(requireAuth);
// Must check if Redis is up to ensure rate limit safety
router.use(requireRedis);

// The chat endpoint uses multer to process multipart/form-data
router.post(
  '/', 
  upload.single('file'), 
  multerErrorHandler, 
  dynamicLimiter, 
  chatController.handleChat
);

// Route for getting chat history
router.get('/:session_id', chatController.getChatHistory);

module.exports = router;
