const { z } = require('zod');

const validateRequest = (schema) => {
  return (req, res, next) => {
    try {
      // Parse request body/query/params against schema
      if (schema.body) {
        req.body = schema.body.parse(req.body);
      }
      if (schema.query) {
        req.query = schema.query.parse(req.query);
      }
      if (schema.params) {
        req.params = schema.params.parse(req.params);
      }
      next();
    } catch (err) {
      next(err);
    }
  };
};

module.exports = {
  validateRequest
};
