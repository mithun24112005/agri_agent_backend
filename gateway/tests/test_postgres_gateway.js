/**
 * PostgreSQL Integration Test for Express Gateway Prisma Models
 * Validates User, Session, RefreshToken models, unique constraints,
 * foreign keys, and cascade deletion against PostgreSQL 'agri_auth'.
 */
const { PrismaClient } = require('@prisma/client');
const crypto = require('crypto');

const prisma = new PrismaClient();

async function runTests() {
  console.log('--- Starting Gateway PostgreSQL Validation Tests ---');
  let passed = 0;
  let total = 0;

  function assert(condition, message) {
    total++;
    if (!condition) {
      console.error(`❌ FAILED: ${message}`);
      throw new Error(`Assertion failed: ${message}`);
    }
    console.log(`✅ PASSED: ${message}`);
    passed++;
  }

  const testId = crypto.randomUUID().slice(0, 8);
  const testEmail = `testuser_${testId}@example.com`;
  const dummyHash = 'argon2id$v=19$m=65536,t=3,p=4$fakeHash1234567890';
  let createdUser = null;

  try {
    // Test 1: Connectivity check
    const pingResult = await prisma.$queryRaw`SELECT 1 as ping`;
    assert(pingResult && pingResult.length > 0 && pingResult[0].ping === 1, 'PostgreSQL database connectivity verified');

    // Test 2: User creation
    createdUser = await prisma.user.create({
      data: {
        email: testEmail,
        passwordHash: dummyHash,
        isActive: true,
      },
    });
    assert(createdUser && createdUser.id && createdUser.email === testEmail, 'User model created with valid UUID');

    // Test 3: Unique email constraint
    let duplicateRejected = false;
    try {
      await prisma.user.create({
        data: {
          email: testEmail,
          passwordHash: dummyHash,
        },
      });
    } catch (err) {
      // Prisma error code P2002 is unique constraint violation
      if (err.code === 'P2002') {
        duplicateRejected = true;
      }
    }
    assert(duplicateRejected, 'Unique constraint on User(email) correctly enforced');

    // Test 4: Session creation with User relation
    const session = await prisma.session.create({
      data: {
        title: 'Spring Crop Planning',
        userId: createdUser.id,
      },
    });
    assert(session && session.userId === createdUser.id, 'Session created and linked to User via foreign key');

    // Test 5: RefreshToken creation with User relation
    const tokenHash = crypto.createHash('sha256').update(`refresh_token_${testId}`).digest('hex');
    const expiresAt = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000);
    const refreshToken = await prisma.refreshToken.create({
      data: {
        userId: createdUser.id,
        tokenHash,
        expiresAt,
      },
    });
    assert(refreshToken && refreshToken.userId === createdUser.id, 'RefreshToken created and linked to User via foreign key');

    // Test 6: Relational query (User with Sessions and RefreshTokens)
    const userWithRelations = await prisma.user.findUnique({
      where: { id: createdUser.id },
      include: {
        sessions: true,
        refreshTokens: true,
      },
    });
    assert(
      userWithRelations.sessions.length === 1 && userWithRelations.refreshTokens.length === 1,
      'Relational query successfully loads foreign key relations'
    );

    // Test 7: Cascade delete verification
    await prisma.user.delete({
      where: { id: createdUser.id },
    });
    createdUser = null; // cleanup marked done

    const remainingSessions = await prisma.session.findMany({
      where: { id: session.id },
    });
    const remainingTokens = await prisma.refreshToken.findMany({
      where: { id: refreshToken.id },
    });
    assert(
      remainingSessions.length === 0 && remainingTokens.length === 0,
      'Cascade deletion verified: child Session and RefreshToken deleted on User delete'
    );

    console.log(`\n🎉 All ${passed}/${total} Gateway PostgreSQL tests PASSED successfully!`);
  } catch (error) {
    console.error('Test execution error:', error);
    process.exitCode = 1;
  } finally {
    if (createdUser) {
      try {
        await prisma.user.delete({ where: { id: createdUser.id } });
      } catch (_) {}
    }
    await prisma.$disconnect();
  }
}

runTests();
