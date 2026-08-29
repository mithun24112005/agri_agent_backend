const prisma = require('../config/database');
const { hashPassword, verifyPassword } = require('../utils/password');
const { generateAccessToken, generateRefreshToken, hashRefreshToken } = require('../services/token.service');
const { AuthenticationError, ValidationError } = require('../utils/errors');

const register = async (req, res, next) => {
  try {
    const { email, password } = req.body;

    const existingUser = await prisma.user.findUnique({ where: { email } });
    if (existingUser) {
      // Do not reveal email exists directly in a highly secure environment, 
      // but for standard apps, a validation error is acceptable.
      throw new ValidationError('Email is already registered');
    }

    const passwordHash = await hashPassword(password);
    
    await prisma.user.create({
      data: {
        email,
        passwordHash
      }
    });

    res.status(201).json({ status: 'success', message: 'Registration successful' });
  } catch (err) {
    next(err);
  }
};

const login = async (req, res, next) => {
  try {
    const { email, password } = req.body;

    const user = await prisma.user.findUnique({ where: { email } });
    if (!user || !user.isActive) {
      throw new AuthenticationError('Invalid email or password');
    }

    const isValid = await verifyPassword(user.passwordHash, password);
    if (!isValid) {
      throw new AuthenticationError('Invalid email or password');
    }

    const accessToken = generateAccessToken(user.id);
    const { token: rawRefreshToken, tokenHash, expiresAt } = generateRefreshToken(user.id);

    // Save refresh token hash in DB
    await prisma.refreshToken.create({
      data: {
        userId: user.id,
        tokenHash,
        expiresAt
      }
    });

    // We send back both tokens
    res.json({
      accessToken,
      refreshToken: rawRefreshToken
    });
  } catch (err) {
    next(err);
  }
};

const refresh = async (req, res, next) => {
  try {
    const { refreshToken } = req.body;
    if (!refreshToken) {
      throw new AuthenticationError('Refresh token required');
    }

    const tokenHash = hashRefreshToken(refreshToken);
    
    // Find the token in DB
    const existingToken = await prisma.refreshToken.findUnique({
      where: { tokenHash },
      include: { user: true }
    });

    if (!existingToken) {
      throw new AuthenticationError('Invalid refresh token');
    }

    if (existingToken.revokedAt) {
      // Security Event: A revoked token is being reused!
      // In a strict implementation, we might revoke ALL refresh tokens for this user.
      console.warn(`[SECURITY] Attempted reuse of revoked refresh token for user ${existingToken.userId}`);
      throw new AuthenticationError('Token has been revoked');
    }

    if (new Date() > existingToken.expiresAt) {
      throw new AuthenticationError('Refresh token expired');
    }

    if (!existingToken.user.isActive) {
      throw new AuthenticationError('User is inactive');
    }

    // Refresh token rotation (transactional)
    const { token: newRawRefreshToken, tokenHash: newTokenHash, expiresAt: newExpiresAt } = generateRefreshToken(existingToken.userId);
    const newAccessToken = generateAccessToken(existingToken.userId);

    await prisma.$transaction([
      prisma.refreshToken.update({
        where: { id: existingToken.id },
        data: { revokedAt: new Date() }
      }),
      prisma.refreshToken.create({
        data: {
          userId: existingToken.userId,
          tokenHash: newTokenHash,
          expiresAt: newExpiresAt
        }
      })
    ]);

    res.json({
      accessToken: newAccessToken,
      refreshToken: newRawRefreshToken
    });
  } catch (err) {
    next(err);
  }
};

const logout = async (req, res, next) => {
  try {
    const { refreshToken } = req.body;
    if (refreshToken) {
      const tokenHash = hashRefreshToken(refreshToken);
      await prisma.refreshToken.updateMany({
        where: { tokenHash, revokedAt: null },
        data: { revokedAt: new Date() }
      });
    }
    res.json({ status: 'success', message: 'Logged out successfully' });
  } catch (err) {
    next(err);
  }
};

const getMe = async (req, res, next) => {
  try {
    const user = await prisma.user.findUnique({
      where: { id: req.user.id },
      select: {
        id: true,
        email: true,
        createdAt: true,
        isActive: true
      }
    });

    if (!user) {
      throw new AuthenticationError('User not found');
    }

    res.json(user);
  } catch (err) {
    next(err);
  }
};

module.exports = {
  register,
  login,
  refresh,
  logout,
  getMe
};
