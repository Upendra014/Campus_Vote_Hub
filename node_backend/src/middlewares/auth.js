const jwt = require('jsonwebtoken');
const AppError = require('../utils/AppError');
const config = require('../config/env');
const User = require('../models/User');

const protect = async (req, res, next) => {
  try {
    let token;
    if (req.headers.authorization && req.headers.authorization.startsWith('Bearer')) {
      token = req.headers.authorization.split(' ')[1];
    }

    if (!token) {
      throw new AppError(401, 'Please authenticate to access this route');
    }

    try {
      const decoded = jwt.verify(token, config.jwt.secret);
      
      const user = await User.findById(decoded.sub);
      if (!user) {
        throw new AppError(401, 'User no longer exists');
      }

      if (user.changedPasswordAfter(decoded.iat)) {
        throw new AppError(401, 'User recently changed password. Please log in again.');
      }

      req.user = user;
      next();
    } catch (err) {
      if (err.name === 'TokenExpiredError') {
        throw new AppError(401, 'Token expired');
      }
      throw new AppError(401, 'Invalid authentication token');
    }
  } catch (error) {
    next(error);
  }
};

const restrictTo = (...roles) => {
  return (req, res, next) => {
    if (!roles.includes(req.user.role)) {
      return next(new AppError(403, 'You do not have permission to perform this action'));
    }
    next();
  };
};

module.exports = { protect, restrictTo };
