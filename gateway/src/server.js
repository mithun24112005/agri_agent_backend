const app = require('./app');
const env = require('./config/env');
const prisma = require('./config/database');

const startServer = async () => {
  try {
    // Check DB connection
    await prisma.$connect();
    console.log('Database connected successfully.');

    const PORT = env.PORT;
    app.listen(PORT, () => {
      console.log(`Express Gateway running on port ${PORT} in ${env.NODE_ENV} mode`);
    });
  } catch (err) {
    console.error('Failed to start server:', err);
    process.exit(1);
  }
};

startServer();
