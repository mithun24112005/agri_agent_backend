const prisma = require('../config/database');
const { AuthorizationError, ValidationError } = require('../utils/errors');
const { proxyChatRequest, proxyGetChatHistory } = require('../services/fastapi.service');

const handleChat = async (req, res, next) => {
  try {
    const { query, session_id } = req.body;
    const file = req.file;

    if (!query) {
      throw new ValidationError('Query is required');
    }
    if (!session_id) {
      throw new ValidationError('Session ID is required');
    }

    // Verify session ownership
    const session = await prisma.session.findUnique({
      where: { id: session_id }
    });

    if (!session) {
      return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Session not found' } });
    }

    if (session.userId !== req.user.id) {
      throw new AuthorizationError('You do not have permission to access this session');
    }

    // Proxy request to FastAPI
    const responseData = await proxyChatRequest(query, session_id, file, req.id);

    res.json(responseData);
  } catch (err) {
    next(err);
  }
};

const getChatHistory = async (req, res, next) => {
  try {
    const { session_id } = req.params;

    // Verify session ownership
    const session = await prisma.session.findUnique({
      where: { id: session_id }
    });

    if (!session) {
      return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Session not found' } });
    }

    if (session.userId !== req.user.id) {
      throw new AuthorizationError('You do not have permission to access this session');
    }

    // Proxy request to FastAPI
    const responseData = await proxyGetChatHistory(session_id, req.id);

    res.json(responseData);
  } catch (err) {
    next(err);
  }
};

module.exports = {
  handleChat,
  getChatHistory
};
