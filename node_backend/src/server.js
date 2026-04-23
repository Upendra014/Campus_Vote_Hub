const app = require('./app');
const config = require('./config/env');
const logger = require('./config/logger');
const connectDB = require('./config/db');

let server;

const startServer = async () => {
  await connectDB();
  
  server = app.listen(config.port, () => {
    logger.info(`Server is listening on port ${config.port} in ${config.env} mode`);
  });
};

startServer();

const exitHandler = () => {
  if (server) {
    server.close(() => {
      logger.info('Server closed');
      process.exit(1);
    });
  } else {
    process.exit(1);
  }
};

const unexpectedErrorHandler = (error) => {
  logger.error(error);
  exitHandler();
};

process.on('uncaughtException', unexpectedErrorHandler);
process.on('unhandledRejection', unexpectedErrorHandler);

process.on('SIGTERM', () => {
  logger.info('SIGTERM received');
  if (server) {
    server.close();
  }
});
