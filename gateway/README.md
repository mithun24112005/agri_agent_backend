# Smart Agriculture Multi-Agent Backend - API Gateway

This directory contains the **Express.js API Gateway** for the Smart Agriculture Multi-Agent Backend system. 

The Gateway serves as the public-facing entry point to the system, acting as a secure proxy and authentication layer in front of the internal LangGraph AI backend.

## 🚀 Key Features

* **Authentication & Authorization**: Full JWT-based authentication flow (Register, Login, Logout) with short-lived access tokens and secure, hashed refresh tokens.
* **Session Management**: Chat sessions are bound to users. The Gateway ensures users can only access and modify their own chat histories.
* **Intelligent Rate Limiting**: Redis-backed rate limiting per IP and per User+IP to protect against abuse and DDoS attacks. Includes fail-safe mechanisms if Redis goes down.
* **Proxying**: Securely proxies authenticated chat requests to the internal FastAPI server using an internal API secret, ensuring the AI service cannot be accessed directly from the outside.
* **Input Validation**: Strict request payload validation using Zod schemas.

## 🛠 Tech Stack

* **Runtime**: Node.js
* **Framework**: Express.js
* **Database**: PostgreSQL (via Prisma ORM)
* **Caching/Rate Limiting**: Redis
* **Security**: Helmet, CORS, Argon2 (Password Hashing), JSON Web Tokens (JWT)
* **Validation**: Zod

## 🏗 Architecture

```mermaid
graph LR
    Client([React frontend :5173]) -->|HTTPS| Gateway[Express API Gateway :3001]
    
    subgraph Gateway Layer
        Gateway --> Auth[Auth & Sessions]
        Gateway --> RL[Redis Rate Limiter]
        Auth --> DB[(PostgreSQL: agri_auth)]
    end
    
    Gateway -->|Internal API Key| FastAPI[FastAPI AI Backend :8001]
    
    subgraph AI Layer
        FastAPI --> LangGraph[LangGraph Agents]
        LangGraph --> StateDB[(PostgreSQL: agri_memory)]
    end
```

## ⚙️ Environment Variables

Create a `.env` file in this directory (or copy from `.env.example`):

```env
# Server Configuration
NODE_ENV=development
PORT=3001
FRONTEND_ORIGIN=http://localhost:5173

# Database Configuration (PostgreSQL agri_auth)
DATABASE_URL="postgresql://postgres:root@localhost:5432/agri_auth?schema=public"

# JWT Configuration
JWT_ACCESS_SECRET=your_super_secret_jwt_key_here
JWT_ACCESS_EXPIRES_IN=15m
JWT_REFRESH_SECRET=your_super_secret_refresh_key_here
JWT_REFRESH_EXPIRES_IN=7d

# Internal API Authentication
INTERNAL_API_SECRET=super_secret_internal_key
FASTAPI_BASE_URL=http://localhost:8001

# Redis Configuration (Rate Limiting)
REDIS_URL=redis://127.0.0.1:6379
```

## 🚀 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Setup the Database
Apply Prisma migrations to create and sync the PostgreSQL database tables:
```bash
npx prisma migrate deploy
```

### 3. Start the Server
Start the development server using nodemon:
```bash
npm run dev
```
For production:
```bash
npm start
```

## 📖 API Documentation

### Auth Routes (`/api/auth`)
* `POST /register`: Register a new user (`email`, `password`)
* `POST /login`: Authenticate and receive tokens
* `POST /refresh`: Issue a new access token using a refresh token
* `POST /logout`: Revoke tokens and logout
* `GET /me`: Get current authenticated user details

### Session Routes (`/api/sessions`)
* `GET /`: Retrieve all chat sessions for the logged-in user
* `POST /`: Create a new chat session (`title`)
* `GET /:id`: Get details for a specific session
* `PATCH /:id`: Rename a chat session (`title`)
* `DELETE /:id`: Delete a chat session

### Chat Routes (`/api/chat`)
* `POST /`: Send a query (and optional image file) to the AI assistant. Proxies the request to the LangGraph backend.
* `GET /:session_id`: Fetch the historical chat messages for a given session.

### Health Routes
* `GET /health`: Check gateway process health.
* `GET /health/ready`: Check gateway readiness.
