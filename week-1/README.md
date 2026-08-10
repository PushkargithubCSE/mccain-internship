# McCain Employee Support AI — Technical Design Document

## 1. Executive Summary

This repository implements a production-style RAG (Retrieval-Augmented Generation) assistant for McCain employees. The solution consists of:

- a Next.js frontend for login, registration, and chat UX,
- a FastAPI backend that exposes REST endpoints and handles authentication,
- a PostgreSQL-backed relational store for user identities,
- Redis for refresh-token session management and rate limiting,
- Qdrant as the vector search layer for policy knowledge retrieval,
- Google Gemini for both embedding generation and final answer synthesis.

The intent is straightforward: employees ask natural-language questions about McCain policy documents, the system retrieves supporting document chunks from a vector store, and the LLM generates a grounded response with company-specific tone and behavior.

This is not just a simple chatbot. It is a layered application with identity management, JWT security, rate limiting, vector retrieval, and document ingestion workflows.

---

## 2. System Goal

The business problem this project solves is knowledge access for a corporate compliance domain.

Instead of forcing employees to manually search a PDF or policy guide, the system supports:

- employee registration and authentication,
- secure access to a policy assistant,
- semantic retrieval over a compliance document,
- answer generation grounded in retrieved chunks,
- a simple web UI for interaction.

In practice, the project behaves like an internal knowledge assistant that must be trustworthy, constrained by organization policy, and operationally safe.

---

## 3. Architectural Overview

### 3.1 High-Level Layers

1. Presentation Layer
   - Next.js app router pages in the frontend.
   - Handles login, registration, chat UI, and bearer token storage in browser local storage.

2. API Layer
   - FastAPI application created in the backend.
   - Router modules are organized under /api/*.
   - The API exposes auth, user, and chat boundaries.

3. Service Layer
   - Business logic for registration, login, sessions, RAG, retrieval, and LLM generation.

4. Data Layer
   - PostgreSQL via SQLAlchemy ORM.
   - Redis for transient state (sessions and rate limiting).
   - Qdrant for vector search over PDF chunks.

5. External AI Layer
   - Gemini embeddings for both query and document vectorization.
   - Gemini LLM for prompt completion.

### 3.2 Request Lifecycle

A typical chat request flows like this:

1. The browser loads the chat page and checks for a valid access token in local storage.
2. If authenticated, the frontend sends a POST request to /api/v1/chat/ask.
3. FastAPI receives the request and validates the payload with Pydantic.
4. The chat route uses the RAG service.
5. The RAG service calls the retrieval service with the user question.
6. Retrieval converts the user query to an embedding using Gemini.
7. Qdrant performs nearest-neighbor semantic search over the indexed knowledge chunks.
8. Top matching chunks are concatenated into a context string.
9. A prompt template is constructed using the retrieved context and the original question.
10. The LLM service sends the prompt to Gemini and returns the generated answer.
11. The API wraps the answer in a standard response envelope and sends it back to the frontend.

---

## 4. Repository Structure

### Backend

The backend is a FastAPI service with a layered architecture:

- app/main.py
  - Application bootstrap and middleware registration.
  - Global exception handlers.
  - Router inclusion.

- app/api/
  - REST entrypoints.
  - auth.py: login, refresh, logout onboarding.
  - user.py: user registration.
  - chat.py: chat health checks and ask route.

- app/core/
  - Configuration, dependency injection, security, logging, exceptions.
  - Central settings object loads environment variables from .env.

- app/db/
  - SQLAlchemy engine setup.
  - Redis client connection.
  - Qdrant client instance.

- app/models/
  - SQLAlchemy models such as User.

- app/repositories/
  - Data-access objects with repository-style CRUD patterns.

- app/schemas/
  - Pydantic request/response models.
  - Strong validation at the API boundary.

- app/services/
  - Business logic for auth, user registration, RAG orchestration, embeddings, LLM calls, retrieval, rate limiting, and sessions.

- app/scripts/
  - Document ingestion utility.

### Frontend

The frontend is a simple Next.js 16 app using the App Router.

- app/page.tsx
  - The primary chat interface.
  - Maintains conversation state.
  - Sends messages to the FastAPI API.

- app/login/page.tsx
  - Auth UI for existing users.

- app/register/page.tsx
  - Sign-up screen for new users.

- public/
  - Static assets such as the McCain brand logo.

---

## 5. Runtime Configuration

The project relies on environment-driven configuration via `BaseSettings` in [Backend/app/core/config.py](week-1/Project1/Backend/app/core/config.py).

Critical env variables include:

- `SECRET_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `GEMINI_API_KEY`

The settings object is cached with `lru_cache`, which keeps reading configuration stable and avoids re-instantiation on every import.

---

## 6. Application Bootstrap and Runtime Behavior

The FastAPI application is created in [Backend/app/main.py](week-1/Project1/Backend/app/main.py).

### Startup Lifecycle

The application startup uses an async lifespan hook:

1. Create relational tables with SQLAlchemy metadata.
2. Ping Redis to verify the connection.
3. Let the application continue serving requests.

During shutdown, it closes the Redis client cleanly.

### Middleware and Global Error Handling

The app registers:

- CORS middleware to allow local frontend development on localhost:3000.
- Logging middleware to capture request/response metadata.
- Exception handlers for custom app exceptions, FastAPI HTTP exceptions, and fallback unhandled exceptions.

This makes the API consistent from an error-handling standpoint and keeps the frontend from receiving raw traceback noise in production.

---

## 7. Backend API Design

The backend is organized around feature routers with prefixes under `/api/v1`.

### 7.1 Auth API

Routes:

- POST /api/v1/auth/login
  - Accepts email + password.
  - Validates email domain (`@mccain.com`).
  - Verifies password using password hashing library integration.
  - Issues JWT access and refresh tokens.
  - Persists the refresh token session in Redis.

- POST /api/v1/auth/refresh
  - Validates refresh token.
  - Ensures token type is refresh.
  - Looks up the session in Redis.
  - Revokes the old session and rotates a new refresh token.

- POST /api/v1/auth/logout
  - Accepts a refresh token.
  - Revokes the associated session entry in Redis.

### 7.2 User API

- POST /api/v1/users/register
  - Creates a new user record in PostgreSQL.
  - Hashes the password before persistence.
  - Rejects duplicate emails with a business error.

### 7.3 Chat API

- GET /api/v1/chat/ping
  - Simple dependency-check endpoint.

- GET /api/v1/chat/error
  - Deliberately raises a custom `AppException` for testing.

- GET /api/v1/chat/test-rate-limit
  - Demonstrates per-user token bucket behavior through Redis.

- POST /api/v1/chat/ask
  - Main chat endpoint.
  - Receives a message string.
  - Executes the RAG pipeline and returns a generated answer.

---

## 8. Security Model

### 8.1 Password Hashing

Passwords are never stored in plaintext. The project uses a password hashing library via `PasswordHash.recommended()`.

Hashing flow:

- registration: hash password before storing in the `users` table,
- login: compare plain input with stored hash,
- token issuance only occurs if the hash check succeeds.

### 8.2 JWT Authentication

Access and refresh tokens are signed with the configured secret key and algorithm (`HS256`).

- Access tokens have a relatively short expiration window.
- Refresh tokens are longer-lived and carry an internal `jti` claim representing a unique refresh session ID.

The `decode_access_token` function enforces that the token is an access token, not a refresh token.

### 8.3 Authorization Dependency

The `get_current_user` function:

1. reads the bearer token from the `Authorization` header,
2. decodes it,
3. looks up the user by ID in PostgreSQL,
4. returns the user object into the protected route.

This pattern keeps route-level authorization centralized.

### 8.4 Session Revocation

Refresh token session state lives in Redis. This allows rotation and revocation semantics:

- each refresh token maps to a session key,
- on refresh, the old session is revoked,
- on logout, the session key is removed,
- if the session does not exist, the refresh flow is rejected.

This is a strong security improvement over blindly accepting refresh tokens forever.

---

## 9. Data Persistence and Database Layer

PostgreSQL is the relational source of truth for user identity.

### 9.1 SQLAlchemy Setup

The project uses SQLAlchemy `create_engine` with connection pooling:

- `pool_pre_ping=True` for stale connection health checks,
- `pool_size=10` and `max_overflow=20` for essential concurrency control.

The session factory is created using `sessionmaker` and exported as `SessionLocal`.

### 9.2 Entity Model

The `User` model includes:

- `id`
- `full_name`
- `email`
- `hashed_password`
- `is_active`

The email is uniquely indexed and the relationship is designed for fast login and user lookup.

### 9.3 Repository Pattern

The repository layer abstracts SQLAlchemy query logic so that service classes stay focused on business rules rather than low-level SQL details.

This is a common SDE pattern: controllers/router call services; services call repositories; repositories talk to ORM models.

---

## 10. Redis Integration

Redis is used for two principal stateful concerns:

1. Session state for refresh-token lifecycle.
2. Rate limiting for the chat endpoint.

### 10.1 Session Service

The session service stores a JSON payload keyed by a token ID:

- `session:<token_id>`
- payload contains `user_id`
- TTL is derived from refresh token lifetime in seconds.

This gives the system a lightweight, centralized revocation mechanism.

### 10.2 Rate Limiter

The `RateLimiter` uses Redis `INCR` to count requests per key and sets an expiration on the first request.

The structure is effectively a fixed-window counter per user. It is simple, fast, and suitable for MVP protection.

---

## 11. Vector Knowledge Retrieval

The retrieval layer is the core of the “AI assistant” behavior.

### 11.1 Document Ingestion Pipeline

The ingestion path lives in the script [Backend/scripts/ingest_pdf.py](week-1/Project1/Backend/scripts/ingest_pdf.py).

The flow is:

1. load a PDF file,
2. split it into documents using LangChain PDF loading,
3. recursively chunk the document text,
4. generate embeddings for each chunk,
5. store those chunks and embeddings in a Qdrant collection.

This script is the offline indexing phase of the system.

### 11.2 Chunking Strategy

The document segmentation uses `RecursiveCharacterTextSplitter` from LangChain, configured with:

- chunk size 800,
- chunk overlap 100,
- separators prioritizing paragraphs and natural boundaries.

This is more robust than naive fixed-window splitting because it preserves semantic coherence and avoids breaking sentences or policy sections arbitrarily.

### 11.3 Qdrant Collection Model

The collection name is `customer_support_knowledge`.

Each point contains:

- vector embedding,
- payload text,
- source file name,
- chunk index.

This enables efficient semantic retrieval with payload metadata attached to each vector entry.

---

## 12. Embedding and Retrieval Services

### 12.1 Embedding Service

The `EmbeddingService` uses the Google Gemini embedding model:

- model: `gemini-embedding-2`
- output dimension: 768

It exposes two operations:

- `embed_text()` for query enrichment and search,
- `embed_documents()` for ingestion-time indexing.

This is the vectorization boundary where natural language becomes numeric representation for nearest-neighbor matching.

### 12.2 Retrieval Service

At query time:

1. convert the user question into an embedding,
2. send it to Qdrant with `query_points`,
3. use payload metadata to reconstruct the hit text,
4. return the top `limit` results.

The service returns a list of dicts with:

- `text`
- `score`
- `chunk_index`

This result set becomes the context passed into the LLM.

---

## 13. RAG Orchestration

The `RAGService` is arguably the most important orchestration class.

### Step-by-Step Execution

1. `retrieval_service.search(question, limit=3)` retrieves the three most relevant chunks.
2. The returned chunk texts are concatenated into one context string.
3. A prompt template defines a role-specific system persona:
   - friendly formal manager tone,
   - policy-first guidance,
   - action-oriented escalation instructions,
   - handling of ambiguous or sensitive scenarios.
4. The prompt template is rendered with `{context}` and `{question}`.
5. `llm_service.generate(prompt)` sends the final assembled prompt to Gemini for response synthesis.

That orchestration is the essence of the application: retrieval provides evidence, and the LLM provides a grounded, human-readable answer.

---

## 14. LLM Service

The LLM integration is implemented in [Backend/app/services/llm_service.py](week-1/Project1/Backend/app/services/llm_service.py).

The service uses `ChatGoogleGenerativeAI` from LangChain and wraps it with a `StrOutputParser`.

The composition is conceptually:

- LLM model instance,
- output parser,
- chain invocation over prompt text.

This simple pattern is clean and efficient for prompt-to-text generation.

---

## 15. Frontend Behavior

The frontend is intentionally lightweight.

### 15.1 Route Behavior

- If no access token exists, the user is redirected from `/` to `/login`.
- After login or registration, the app stores tokens in browser local storage.
- The chat page loads messages from the UI state, not from persistent server-side storage.

### 15.2 Chat UX

The conversation component:

- allows user input,
- adds user messages to local state immediately,
- sends a POST request to the backend chat endpoint,
- appends the generated assistant answer,
- handles loading and error fallback messages.

### 15.3 Client-Server Contract

The frontend makes direct API requests to the backend at `http://127.0.0.1:8000` and sends:

- `Content-Type: application/json`
- `Authorization: Bearer <access_token>` for protected routes.

This is a straightforward local-development architecture without a separate gateway or reverse proxy layer.

---

## 16. API Response Shape

The project standardizes success and failure responses through a reusable envelope.

Typical success envelope:

- `success: true`
- `message: "..."`
- `data: {...}`

Typical error envelope:

- `success: false`
- `message: "..."`
- `error_code: "..."` for custom exceptions.

This consistency helps the frontend render predictable UI states.

---

## 17. Dependency Stack Summary

### Core Runtime

- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic + Pydantic Settings
- Redis client
- Qdrant client

### Auth + Security

- `python-jose` for JWT handling
- `passlib[bcrypt]` for password hashing
- `python-multipart` for multipart support

### AI / Retrieval

- LangChain
- LangChain OpenAI integration
- LangChain community
- Gemini embeddings and Gemini LLM access
- `sentence-transformers`, `tiktoken`

### Document Processing

- `pypdf`
- `langchain_community.document_loaders.PyPDFLoader`
- `RecursiveCharacterTextSplitter`

### Testing and Quality

- pytest
- pytest-asyncio
- httpx
- black, isort, flake8

---

## 18. Runtime Notes and Operational Considerations

### 18.1 This Project is Infrastructure-Dependent

A fully functional local instance requires:

- PostgreSQL
- Redis
- Qdrant
- Gemini API access

The code connects to these external systems directly, which is acceptable for an MVP but not ideal for a high-scale production deployment.

### 18.2 Current Limitations

A few design and implementation constraints are worth noting:

- the frontend stores JWTs in browser storage, which is practical for demos but less ideal than secure httpOnly cookie patterns,
- the chat UI is not persisted server-side beyond the vector retrieval and RAG result,
- the ingestion path is script-driven, not yet packaged as a production task pipeline,
- the backend uses direct DB and external-service wiring rather than a fully abstracted deployable service mesh.

### 18.3 What Would Be Next in Production

A senior SDE would likely improve the following next:

- move to a containerized deployment with Docker Compose,
- use environment-specific secrets management,
- add a database migration workflow for controlled schema changes,
- add observability: structured logs, traces, metrics,
- enforce per-user auth + RBAC for admin and non-admin knowledge operations,
- add async job workers for ingestion and embedding generation,
- introduce a true user session store abstraction instead of ad hoc Redis keys.

---

## 19. Example End-to-End Walkthrough

Suppose a McCain employee asks: “What is the policy on conflicts of interest?”

The flow would be:

1. Browser sends the question via the chat UI.
2. Backend receives the request and uses the `RAGService`.
3. The retrieval service turns the question into a vector embedding.
4. Qdrant returns the most semantically relevant policy chunks.
5. The prompt template injects those chunks into the system prompt.
6. Gemini produces an answer in a friendly formal tone, grounded in the retrieved evidence.
7. The answer is delivered to the UI as JSON payload.

The key idea is that the LLM does not hallucinate the answer from general knowledge alone; it is constrained by retrieved company document context.

---

## 20. Summary

This project is a practical internal enterprise RAG application with the following design shape:

- Next.js frontend for the user experience,
- FastAPI for the HTTP backbone,
- SQLAlchemy + PostgreSQL for identity persistence,
- Redis for session and rate-limit state,
- Qdrant for semantic access to document knowledge,
- Gemini for both embeddings and answer generation.

The codebase is intentionally structured to be understandable and extensible. Each layer has a clear responsibility, and the application demonstrates a real world pattern: route → service → repository/model → external vector/LLM system.

That is the central engineering story of the repository.
