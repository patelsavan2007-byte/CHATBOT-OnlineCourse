# CHARUSAT Online Course Assistant

A terminal-based RAG chatbot that answers questions using a local university knowledge base.

## Features

- Loads all `.txt` and `.md` files in the knowledge base folder
- Splits content into overlapping chunks
- Embeds chunks with Hugging Face embeddings
- Stores vectors in a local Chroma database
- Retrieves the top relevant chunks for each query
- Uses a grounded prompt that refuses to hallucinate
- Runs entirely in the terminal with Rich-based output

## Folder Structure

```text
backend/
├── knowledge_base/
├── vector_db/
├── app/
│   ├── ingestion.py
│   ├── embeddings.py
│   ├── retriever.py
│   ├── llm.py
│   ├── rag_chain.py
│   ├── prompt.py
│   ├── chatbot.py
│   ├── utils.py
│   └── config.py
├── main.py
├── requirements.txt
└── README.md
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the backend folder with one of the following:

```env
GOOGLE_API_KEY=your_google_api_key
# or
OPENAI_API_KEY=your_openai_key
```

## Build the Vector Database

```bash
python ingestion.py
```

This deletes the old vector store, re-ingests the knowledge base, and rebuilds the Chroma index.

## Run the Chatbot

```bash
python main.py
```
