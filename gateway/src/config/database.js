require('dotenv').config();
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient({
  log: process.env.NODE_ENV === 'development' ? ['error', 'warn'] : ['error'],
});

const handleDisconnect = async () => {
  try {
    await prisma.$disconnect();
  } catch (err) {
    console.error('Error during database disconnect:', err.message);
  }
};

process.on('beforeExit', handleDisconnect);
process.on('SIGINT', async () => {
  await handleDisconnect();
  process.exit(0);
});
process.on('SIGTERM', async () => {
  await handleDisconnect();
  process.exit(0);
});

module.exports = prisma;
