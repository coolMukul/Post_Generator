**High-Level Concept:**
User interacts with a separate UI project that connects to a backend API. The system ingests multiple public documents (URL or file upload) and stores them in pgvector. A test UI screen validates each agent and phase during development. The final UI provides a textbox where users enter text, the application recommends matching ingested documents, users select documents, the application asks targeted questions, and then generates a copy-paste-ready LinkedIn post.

## Guiding Principles

**Cost:** Use free APIs for personal use where possible.
**Quality:** Follow industry best practices targeting scalable enterprise architecture.
**Observability:** Console logs required to track agent and tool progress.
**Dependencies:** Minimize new dependencies; reuse existing ones.
**Documentation:** All documents should be created in mukDocs folder. Prefix with Phase number in case its phase related.
**Github** Prefix Phase number to the branch if created e.g. Phase1-, Phase2-

## Coding Guidelines
- All md files should be in mukDocs folder.
- mukDocs\TODO.md keeps track of upcoming changes and changes done for each phase at medium detail level in chronological order. 
    - Upcoming Changes at top. Remove the changes from TODO list only when they are completed and tested. TODO list can be increased to make sure nothing is missed from tracking.
    - Followed by Changes that are completed. Within completed changes, recent changes at top while earlier changes at bottom.
- api should call handlers and submit a bullmq job. Only chatting related scenario will have syncronouse pattern.
- api should use FastAPI and swagger.
- use zod or something similar for strict type check
- sharable objects, data types, schema, etc to be placed in types folder
- No cyclic refrences
- External system (e.g. ui) should poll the api to check job status. Job output is json.
- Job status are 
    - Failed with Error message, Start time, End time
    - Success with job result, Start time, End time
    - InProgress with Start time
- Later we intend to implement SSE(out of scope for now), but code should have option to easily extend this feature.
- STRICTLY no mock up data or function to be created until asked to do so. If mock up functions created when asked mention it in TODO.md file.
- STRICTLY no TO DO in code.
- STRICTLY no fallback code required.
- workers and api project in python while ui will be in react. 
- workers
    - only one main queue for types of jobs
    - handler receives message from api and submits a job
    - Steps are logged in console logs for tracing. e.g. Logging matching score is beneficial than long DB result. 
    - Log job start and job complete in console logs. 
    - On exception log the error in console logs and make result as failed for the job with error message.
- unit-test 
    - Add unit test cases inside unit-test folder for testing each phase. 
    - Prefix the unit test case with Phase number  e.g. Phase1-, Phase2-.
    - Insert recent unit test cases at top.
    - Update the mukDocs\UnitTestResult.md file with high level summary of unit test cases execution result. Delete old results as they are redundant.
- No business logic in api layer. Business logic and db access will always remains in workers.

### What You CAN'T Use
❌ Any code from any company IP or licensed sources

### What You CAN Use
✅ Architectural patterns learned (multi-agent, RAG, StateGraph)
✅ Technology choices (LangGraph, Fastify, Next.js, pgvector)
✅ Design principles (per-tenant isolation, hybrid search, contextual embeddings)
✅ Your expertise in building these systems
✅ Public knowledge from LangChain/LangGraph documentation

---


## Project Structure

```
post_generator/
├── src/
│   ├── api/              # FastAPI routes
│   ├── workers/          # Background tasks (Celery/ARQ)
│   │   └── agents/       # LangGraph agents
│   ├── services/         # Shared business logic
│   ├── repositories/     # Data access
│   ├── models/           # Pydantic schemas
│   └── config/           # Settings
├── unit-test/
├── scripts/              # DB migrations, utilities
├── pyproject.toml
├── .env
├── mukDocs/
└── README.md
```