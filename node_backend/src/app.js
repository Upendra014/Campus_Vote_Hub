const express = require('express');
const helmet = require('helmet');
const xss = require('xss-clean');
const mongoSanitize = require('express-mongo-sanitize');
const hpp = require('hpp');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const config = require('./config/env');
const morgan = require('morgan');
const logger = require('./config/logger');
const { errorConverter, errorHandler } = require('./middlewares/errorHandler');
const AppError = require('./utils/AppError');

const app = express();

// Set security HTTP headers
app.use(helmet());

// Logging
if (config.env !== 'test') {
  app.use(morgan.successHandler || morgan('dev'));
  app.use(morgan.errorHandler || morgan('dev'));
}

// Global rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.',
});
app.use('/api', limiter);

// Parse json request body
app.use(express.json({ limit: '10kb' }));

// Parse urlencoded request body
app.use(express.urlencoded({ extended: true, limit: '10kb' }));

// Data sanitization against NoSQL query injection
app.use(mongoSanitize());

// Data sanitization against XSS
app.use(xss());

// Prevent parameter pollution
app.use(hpp());

// Enable CORS
app.use(cors({
  origin: config.cors.origin,
  credentials: true
}));

// Routes
app.use('/api/v1/auth', require('./routes/authRoutes'));
app.use('/api/v1/events', require('./routes/eventRoutes'));
app.use('/api/v1/votes', require('./routes/voteRoutes'));

app.get('/health', (req, res) => {
  res.status(200).json({ 
    success: true, 
    message: 'Backend is running securely',
    version: '2.0.0'
  });
});

// Send back a 404 error for any unknown api request
app.all('*', (req, res, next) => {
  next(new AppError(404, `Not found: ${req.originalUrl}`));
});

// Convert error to AppError, if needed
app.use(errorConverter);

// Handle error
app.use(errorHandler);

module.exports = app;
