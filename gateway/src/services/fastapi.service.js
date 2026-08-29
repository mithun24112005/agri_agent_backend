const axios = require('axios');
const FormData = require('form-data');
const env = require('../config/env');
const { AppError } = require('../utils/errors');

const apiClient = axios.create({
  baseURL: env.FASTAPI_BASE_URL,
  timeout: 60000, // 60s timeout for LangGraph processing
  headers: {
    'X-Internal-API-Key': env.INTERNAL_API_SECRET
  }
});

/**
 * Forward chat request to FastAPI
 */
const proxyChatRequest = async (query, sessionId, file, requestId) => {
  try {
    const form = new FormData();
    form.append('query', query);
    form.append('session_id', sessionId);
    
    if (file) {
      form.append('file', file.buffer, {
        filename: file.originalname,
        contentType: file.mimetype
      });
    }

    const response = await apiClient.post('/chat', form, {
      headers: {
        ...form.getHeaders(),
        'X-Request-ID': requestId // correlate logs
      },
      // Do NOT retry automatically since /chat is stateful (LangGraph)
    });

    return response.data;
  } catch (error) {
    if (error.response) {
      // FastAPI returned an error status
      throw new AppError(
        error.response.data?.detail || 'AI Service Error',
        error.response.status,
        'AI_SERVICE_ERROR'
      );
    } else if (error.code === 'ECONNABORTED') {
      throw new AppError('AI Service timeout', 504, 'AI_SERVICE_TIMEOUT');
    } else {
      throw new AppError('AI Service unavailable', 502, 'AI_SERVICE_UNAVAILABLE');
    }
  }
};

/**
 * Fetch chat history from FastAPI
 */
const proxyGetChatHistory = async (sessionId, requestId) => {
  try {
    const response = await apiClient.get(`/chat/${sessionId}`, {
      headers: {
        'X-Request-ID': requestId
      }
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new AppError(
        error.response.data?.detail || 'AI Service Error',
        error.response.status,
        'AI_SERVICE_ERROR'
      );
    } else {
      throw new AppError('AI Service unavailable', 502, 'AI_SERVICE_UNAVAILABLE');
    }
  }
};

module.exports = {
  proxyChatRequest,
  proxyGetChatHistory
};
