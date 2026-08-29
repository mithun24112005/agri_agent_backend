const express = require('express');
const { requireAuth } = require('../middleware/auth.middleware');
const sessionController = require('../controllers/session.controller');

const router = express.Router();

// All session routes require authentication
router.use(requireAuth);

router.post('/', sessionController.createSession);
router.get('/', sessionController.getSessions);
router.get('/:id', sessionController.getSessionById);
router.patch('/:id', sessionController.updateSession);
router.delete('/:id', sessionController.deleteSession);

module.exports = router;
