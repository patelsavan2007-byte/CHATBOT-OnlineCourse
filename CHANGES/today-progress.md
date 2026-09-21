# Today’s Progress

## Completed

- Built a terminal-based RAG chatbot for the CHARUSAT online course knowledge base.
- Created a backend-only structure without any frontend.
- Added knowledge-base ingestion for `.txt` and `.md` files.
- Implemented chunking with metadata for each document chunk.
- Added embedding generation and local ChromaDB vector storage.
- Implemented retrieval of the top relevant chunks with source and similarity details.
- Added a command-line chat loop so users can ask questions in the terminal.
- Added project documentation and dependency files for backend setup.

## Files Added

- `backend/main.py`
- `backend/ingestion.py`
- `backend/app/config.py`
- `backend/app/utils.py`
- `backend/app/ingestion.py`
- `backend/app/embeddings.py`
- `backend/app/retriever.py`
- `backend/app/llm.py`
- `backend/app/prompt.py`
- `backend/app/rag_chain.py`
- `backend/app/chatbot.py`
- `backend/requirements.txt`
- `backend/README.md`

## How to Run

```powershell
cd C:\AProjects\CHATB\CHATBOT-OnlineCourse
.\venv\Scripts\python.exe backend\ingestion.py
.\venv\Scripts\python.exe backend\main.py
```

## Notes

- The chatbot answers using retrieved context from the knowledge base.
- It can run in the terminal without any frontend.
- A `.env` file was added for optional API key configuration.
