const Joi = require('joi');
const AppError = require('../utils/AppError');

const validate = (schema) => (req, res, next) => {
  const validSchema = typeof schema === 'function' ? schema(req) : schema;
  const object = {};
  
  ['params', 'query', 'body'].forEach((key) => {
    if (Object.keys(validSchema).includes(key)) {
      object[key] = req[key];
    }
  });
  
  const { value, error } = Joi.compile(validSchema)
    .prefs({ errors: { label: 'key' }, abortEarly: false })
    .validate(object);

  if (error) {
    const errorMessage = error.details.map((details) => details.message).join(', ');
    return next(new AppError(400, errorMessage));
  }
  
  Object.assign(req, value);
  return next();
};

module.exports = validate;
