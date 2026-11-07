const prisma = require('../config/database');
const { AuthorizationError, ValidationError } = require('../utils/errors');
const { proxyChatRequest, proxyGetChatHistory } = require('../services/fastapi.service');

const handleChat = async (req, res, next) => {
  try {
    const { query, session_id } = req.body;
    const file = req.file;

    if (!query) {
      throw new ValidationError('Query is required');
    }
    if (!session_id) {
      throw new ValidationError('Session ID is required');
    }

    // Verify session ownership
    const session = await prisma.session.findUnique({
      where: { id: session_id }
    });

    if (!session) {
      return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Session not found' } });
    }

    if (session.userId !== req.user.id) {
      throw new AuthorizationError('You do not have permission to access this session');
    }

    // Proxy request to FastAPI with user identity
    const responseData = await proxyChatRequest(query, session_id, file, req.id, req.user.id);

    // Persist messages and agent execution records in PostgreSQL
    try {
      // 1. User message
      await prisma.message.create({
        data: {
          sessionId: session_id,
          role: 'user',
          content: query,
          metadata: file ? { filename: file.originalname, size: file.size } : null
        }
      });

      // 2. Assistant response
      const assistantMessage = await prisma.message.create({
        data: {
          sessionId: session_id,
          role: 'assistant',
          content: responseData.response || '',
          metadata: {
            selected_agents: responseData.selected_agents || [],
            agent_responses: responseData.agent_responses || {}
          }
        }
      });

      // 3. AgentRun records
      if (Array.isArray(responseData.selected_agents) && responseData.selected_agents.length > 0) {
        const agentRunData = responseData.selected_agents.map(agent => ({
          messageId: assistantMessage.id,
          agentName: agent,
          status: 'success'
        }));
        await prisma.agentRun.createMany({ data: agentRunData });
      }
    } catch (dbErr) {
      console.error('[GATEWAY DB ERROR] Failed to persist chat history:', dbErr);
      // Non-blocking: ensure user response is still delivered even if logging fails
    }

    res.json(responseData);
  } catch (err) {
    next(err);
  }
};

const getChatHistory = async (req, res, next) => {
  try {
    const { session_id } = req.params;

    // Verify session ownership
    const session = await prisma.session.findUnique({
      where: { id: session_id }
    });

    if (!session) {
      return res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Session not found' } });
    }

    if (session.userId !== req.user.id) {
      throw new AuthorizationError('You do not have permission to access this session');
    }

    // 1. Attempt to fetch from FastAPI session checkpointer
    try {
      const responseData = await proxyGetChatHistory(session_id, req.id);
      if (responseData && responseData.messages && responseData.messages.length > 0) {
        return res.json(responseData);
      }
    } catch (proxyErr) {
      console.warn('[GATEWAY] FastAPI history fetch failed, falling back to database messages:', proxyErr.message);
    }

    // 2. Fallback: Read directly from PostgreSQL Message table
    const dbMessages = await prisma.message.findMany({
      where: { sessionId: session_id },
      orderBy: { createdAt: 'asc' }
    });

    res.json({
      status: 'success',
      session_id,
      messages: dbMessages.map(m => ({
        role: m.role,
        content: m.content,
        created_at: m.createdAt
      }))
    });
  } catch (err) {
    next(err);
  }
};

module.exports = {
  handleChat,
  getChatHistory
};
