const { AppError } = require('../utils/errors');

const errorHandler = (err, req, res, next) => {
  // If the error is an operational AppError, we can send its specific code and message.
  // Otherwise, it's a programming or unknown error, so we mask the details.
  
  if (err.name === 'ZodError') {
    return res.status(400).json({
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Invalid request data',
        details: err.errors
      }
    });
  }

  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      error: {
        code: err.code,
        message: err.message
      }
    });
  }

  // Mask internal errors (e.g. Prisma errors, Axios errors to FastAPI, etc.)
  console.error(`[Error] ReqID: ${req.id || 'unknown'} - `, err);
  
  return res.status(500).json({
    error: {
      code: 'INTERNAL_SERVER_ERROR',
      message: 'An unexpected error occurred'
    }
  });
};

module.exports = {
  errorHandler
};
