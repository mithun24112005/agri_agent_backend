const prisma = require('../config/database');
const { ValidationError, AuthorizationError } = require('../utils/errors');

const createSession = async (req, res, next) => {
  try {
    const { title } = req.body;
    if (!title) {
      throw new ValidationError('Session title is required');
    }

    const session = await prisma.session.create({
      data: {
        title,
        userId: req.user.id
      }
    });

    res.status(201).json(session);
  } catch (err) {
    next(err);
  }
};

const getSessions = async (req, res, next) => {
  try {
    const sessions = await prisma.session.findMany({
      where: { userId: req.user.id },
      orderBy: { updatedAt: 'desc' }
    });
    res.json(sessions);
  } catch (err) {
    next(err);
  }
};

const getSessionById = async (req, res, next) => {
  try {
    const { id } = req.params;
    
    const session = await prisma.session.findUnique({
      where: { id }
    });

    if (!session) {
      return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Session not found' } });
    }

    if (session.userId !== req.user.id) {
      throw new AuthorizationError('You do not have permission to access this session');
    }

    res.json(session);
  } catch (err) {
    next(err);
  }
};

const deleteSession = async (req, res, next) => {
  try {
    const { id } = req.params;

    const session = await prisma.session.findUnique({
      where: { id }
    });

    if (!session) {
      return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Session not found' } });
    }

    if (session.userId !== req.user.id) {
      throw new AuthorizationError('You do not have permission to delete this session');
    }

    await prisma.session.delete({
      where: { id }
    });

    res.json({ status: 'success', message: 'Session deleted' });
  } catch (err) {
    next(err);
  }
};

const updateSession = async (req, res, next) => {
  try {
    const { id } = req.params;
    const { title } = req.body;

    if (!title) {
      throw new ValidationError('Session title is required');
    }

    const session = await prisma.session.findUnique({
      where: { id }
    });

    if (!session) {
      return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Session not found' } });
    }

    if (session.userId !== req.user.id) {
      throw new AuthorizationError('You do not have permission to modify this session');
    }

    const updatedSession = await prisma.session.update({
      where: { id },
      data: { title }
    });

    res.json(updatedSession);
  } catch (err) {
    next(err);
  }
};

module.exports = {
  createSession,
  getSessions,
  getSessionById,
  deleteSession,
  updateSession
};
