const { AuthenticationError } = require('../utils/errors');
const { verifyAccessToken } = require('../services/token.service');
const prisma = require('../config/database');

const requireAuth = async (req, res, next) => {
  try {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      throw new AuthenticationError('No access token provided');
    }

    const token = authHeader.split(' ')[1];
    const decoded = verifyAccessToken(token);

    if (!decoded) {
      throw new AuthenticationError('Invalid or expired access token');
    }

    // Ensure the user still exists and is active
    const user = await prisma.user.findUnique({
      where: { id: decoded.sub }
    });

    if (!user || !user.isActive) {
      throw new AuthenticationError('User no longer exists or is inactive');
    }

    // Attach user identity to request. Never trust frontend ID.
    req.user = { id: user.id };
    
    next();
  } catch (err) {
    next(err);
  }
};

module.exports = {
  requireAuth
};
