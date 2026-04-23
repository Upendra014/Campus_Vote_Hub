const dotenv = require('dotenv');
const Joi = require('joi');
const path = require('path');

dotenv.config({ path: path.join(__dirname, '../../.env') });

const envVarsSchema = Joi.object({
  NODE_ENV: Joi.string().valid('production', 'development', 'test').required(),
  PORT: Joi.number().default(5000),
  MONGO_URI: Joi.string().required().description('Mongo DB URL'),
  JWT_SECRET: Joi.string().required().description('JWT Secret key'),
  JWT_EXPIRE: Joi.string().default('15m'),
  JWT_REFRESH_SECRET: Joi.string().required().description('JWT Refresh Secret key'),
  JWT_REFRESH_EXPIRE: Joi.string().default('7d'),
  CORS_ORIGIN: Joi.string().required().description('CORS allowed origin'),
  ADMIN_EMAIL: Joi.string().email().required(),
  ADMIN_PASSWORD: Joi.string().required(),
}).unknown();

const { value: envVars, error } = envVarsSchema.prefs({ errors: { label: 'key' } }).validate(process.env);

if (error) {
  throw new Error(`Config validation error: ${error.message}`);
}

module.exports = {
  env: envVars.NODE_ENV,
  port: envVars.PORT,
  mongoose: {
    url: envVars.MONGO_URI,
    options: {
    },
  },
  jwt: {
    secret: envVars.JWT_SECRET,
    accessExpiration: envVars.JWT_EXPIRE,
    refreshSecret: envVars.JWT_REFRESH_SECRET,
    refreshExpiration: envVars.JWT_REFRESH_EXPIRE,
  },
  cors: {
    origin: envVars.CORS_ORIGIN
  },
  admin: {
    email: envVars.ADMIN_EMAIL,
    password: envVars.ADMIN_PASSWORD
  }
};
