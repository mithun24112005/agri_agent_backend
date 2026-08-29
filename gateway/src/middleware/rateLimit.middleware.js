const { createClient } = require('redis');
const { rateLimit } = require('express-rate-limit');
const { RedisStore } = require('rate-limit-redis');
const env = require('../config/env');

// Redis Client
const redisClient = createClient({
  url: env.REDIS_URL
});

redisClient.on('error', (err) => console.error('[Redis Error]', err));
redisClient.on('connect', () => console.log('Redis connected for rate limiting'));

// Attempt connection but don't crash if it fails
(async () => {
  try {
    await redisClient.connect();
  } catch (err) {
    console.error('Initial Redis connection failed:', err);
  }
})();

// Create rate limiter factory
const createLimiter = (options) => {
  return rateLimit({
    store: new RedisStore({
      sendCommand: (...args) => redisClient.sendCommand(args),
      prefix: options.prefix
    }),
    windowMs: options.windowMs,
    max: options.max,
    message: {
      error: {
        code: 'RATE_LIMIT_EXCEEDED',
        message: 'Too many requests, please try again later.'
      }
    },
    standardHeaders: true,
    legacyHeaders: false,
    keyGenerator: options.keyGenerator,
    // Redis Failure handling: fallback to 503
    handler: (req, res, next, options) => {
      // express-rate-limit default handler sends 429.
      // If store is unavailable, it could bypass. We ensure proper error if Redis is down.
      if (!redisClient.isReady) {
        return res.status(503).json({
          error: {
            code: 'SERVICE_UNAVAILABLE',
            message: 'Rate limiting service is temporarily unavailable.'
          }
        });
      }
      res.status(options.statusCode).json(options.message);
    },
    // Pass to handler if store is down
    passOnStoreError: false, 
  });
};

// 1. IP-based Auth Limiters
const registerLimiter = createLimiter({
  prefix: 'rl:register:ip:',
  windowMs: 60 * 60 * 1000, // 1 hour
  max: env.RATE_LIMIT_REGISTER,
  keyGenerator: (req) => req.ip
});

const loginLimiter = createLimiter({
  prefix: 'rl:login:ip:',
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: env.RATE_LIMIT_LOGIN,
  keyGenerator: (req) => req.ip
});

// 2. User-based Limiters (requires req.user to be set by requireAuth)
const chatLimiter = createLimiter({
  prefix: 'rl:chat:user_ip:',
  windowMs: 60 * 1000, // 1 minute
  max: env.RATE_LIMIT_CHAT,
  keyGenerator: (req) => {
    if (!req.user) return req.ip;
    return `${req.user.id}:${req.ip}`;
  }
});

const imageLimiter = createLimiter({
  prefix: 'rl:image:user_ip:',
  windowMs: 60 * 1000, // 1 minute
  max: env.RATE_LIMIT_IMAGE,
  keyGenerator: (req) => {
    if (!req.user) return req.ip;
    return `${req.user.id}:${req.ip}`;
  }
});

// Middleware to manually check Redis readiness for endpoints where rate limit is critical
const requireRedis = (req, res, next) => {
  if (!redisClient.isReady) {
    return res.status(503).json({
      error: {
        code: 'SERVICE_UNAVAILABLE',
        message: 'Service is temporarily unavailable (Rate limiter down).'
      }
    });
  }
  next();
};

module.exports = {
  redisClient,
  registerLimiter,
  loginLimiter,
  chatLimiter,
  imageLimiter,
  requireRedis
};
