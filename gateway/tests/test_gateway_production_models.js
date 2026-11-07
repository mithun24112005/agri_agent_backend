const { PrismaClient } = require('@prisma/client');
const crypto = require('crypto');

const prisma = new PrismaClient();

async function runTests() {
  console.log('--- Starting Gateway Production Models Validation Tests ---');
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
  const testEmail = `produser_${testId}@example.com`;
  const dummyHash = 'argon2id$v=19$m=65536,t=3,p=4$fakeHash1234567890';
  let user = null;
  let session = null;

  try {
    // 1. Create User & Session
    user = await prisma.user.create({
      data: { email: testEmail, passwordHash: dummyHash, isActive: true }
    });
    session = await prisma.session.create({
      data: { title: 'Test Session', userId: user.id }
    });
    assert(user && session, 'User and Session initialized');

    // 2. Test Message model
    const userMsg = await prisma.message.create({
      data: {
        sessionId: session.id,
        role: 'user',
        content: 'Recommend crop for N=90, P=40, K=40, pH=6.5',
      }
    });
    const assistantMsg = await prisma.message.create({
      data: {
        sessionId: session.id,
        role: 'assistant',
        content: 'Rice is recommended based on soil parameters.',
        metadata: { tokensUsed: 150, latencyMs: 1200 }
      }
    });
    assert(userMsg && assistantMsg, 'Message models (user & assistant) created successfully');

    // 3. Test AgentRun model
    const agentRun = await prisma.agentRun.create({
      data: {
        messageId: assistantMsg.id,
        agentName: 'crop_agent',
        status: 'success',
        durationMs: 850
      }
    });
    assert(agentRun && agentRun.agentName === 'crop_agent', 'AgentRun model created with foreign key to Message');

    // 4. Test CropRecommendation model
    const cropRec = await prisma.cropRecommendation.create({
      data: {
        userId: user.id,
        sessionId: session.id,
        recommendedCrop: 'rice',
        confidence: 0.85,
        n: 90.0,
        p: 40.0,
        k: 40.0,
        ph: 6.5,
        temperature: 25.0,
        humidity: 80.0,
        rainfall: 200.0,
        alternatives: [{ crop: 'jute', vote: 0.10 }, { crop: 'cotton', vote: 0.05 }]
      }
    });
    assert(cropRec && cropRec.recommendedCrop === 'rice', 'CropRecommendation model created successfully');

    // 5. Test DiseasePrediction model
    const diseasePred = await prisma.diseasePrediction.create({
      data: {
        userId: user.id,
        sessionId: session.id,
        imageKey: 'img_test_123.jpg',
        predictedClass: 'Tomato___Early_blight',
        confidence: 0.945,
        isHealthy: false,
        treatment: { organic: 'Neem oil spray', chemical: 'Mancozeb' }
      }
    });
    assert(diseasePred && diseasePred.predictedClass === 'Tomato___Early_blight', 'DiseasePrediction model created successfully');

    // 6. Test Feedback model
    const feedback = await prisma.feedback.create({
      data: {
        userId: user.id,
        messageId: assistantMsg.id,
        rating: 5,
        comment: 'Very helpful agronomic advice!'
      }
    });
    assert(feedback && feedback.rating === 5, 'Feedback model created successfully');

    // 7. Test FarmProfile model
    const farmProfile = await prisma.farmProfile.create({
      data: {
        userId: user.id,
        farmName: 'Green Acres Farm',
        acreage: 12.5,
        soilType: 'Clay Loam',
        primaryCrops: ['rice', 'wheat', 'mustard'],
        location: { state: 'Punjab', district: 'Ludhiana', village: 'Khanna' }
      }
    });
    assert(farmProfile && farmProfile.farmName === 'Green Acres Farm', 'FarmProfile model created successfully');

    // 8. Test Cascade Deletion: Deleting user cascades all related models
    await prisma.user.delete({ where: { id: user.id } });
    const checkSession = await prisma.session.findUnique({ where: { id: session.id } });
    const checkMsg = await prisma.message.findUnique({ where: { id: userMsg.id } });
    const checkFarm = await prisma.farmProfile.findUnique({ where: { id: farmProfile.id } });
    const checkCrop = await prisma.cropRecommendation.findUnique({ where: { id: cropRec.id } });
    const checkDis = await prisma.diseasePrediction.findUnique({ where: { id: diseasePred.id } });
    
    assert(!checkSession && !checkMsg && !checkFarm && !checkCrop && !checkDis, 'Cascade deletion cleaned up all associated records');

    console.log(`\n🎉 All ${passed}/${total} Gateway Production Models tests PASSED successfully!`);
  } catch (err) {
    console.error('Test execution error:', err);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

runTests();
