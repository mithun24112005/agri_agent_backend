require('dotenv').config();

const env = {
  PORT: process.env.PORT || 3000,
  NODE_ENV: process.env.NODE_ENV || 'development',
  JWT_ACCESS_SECRET: process.env.JWT_ACCESS_SECRET,
  JWT_REFRESH_SECRET: process.env.JWT_REFRESH_SECRET,
  JWT_ACCESS_EXPIRES_IN: process.env.JWT_ACCESS_EXPIRES_IN || '15m',
  JWT_REFRESH_EXPIRES_IN: process.env.JWT_REFRESH_EXPIRES_IN || '7d',
  REDIS_URL: process.env.REDIS_URL || 'redis://localhost:6379',
  FASTAPI_BASE_URL: process.env.FASTAPI_BASE_URL || 'http://localhost:8001',
  INTERNAL_API_SECRET: process.env.INTERNAL_API_SECRET,
  FRONTEND_ORIGIN: process.env.FRONTEND_ORIGIN || 'http://localhost:8501',
  RATE_LIMIT_LOGIN: parseInt(process.env.RATE_LIMIT_LOGIN || '10', 10),
  RATE_LIMIT_REGISTER: parseInt(process.env.RATE_LIMIT_REGISTER || '5', 10),
  RATE_LIMIT_CHAT: parseInt(process.env.RATE_LIMIT_CHAT || '30', 10),
  RATE_LIMIT_IMAGE: parseInt(process.env.RATE_LIMIT_IMAGE || '10', 10),
};

module.exports = env;
