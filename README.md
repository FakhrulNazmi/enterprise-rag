# Enterprise Local RAG Web Assistant

A full-stack, 100% free, privacy-first **Retrieval-Augmented Generation (RAG)** web application designed for corporate internal knowledge ingestion. Administrators can securely parse operational manuals or order processing PDFs, allowing users to query documentation via local AI with exact page-level source citations.

## 🏗️ System Architecture

```text
[ Admin UI ] ──( Multipart Form PDF )──> [ FastAPI Core ]
                                               │
                                      (PyMuPDF Parsing &
                                     Recursive Chunking)
                                               │
                                               ▼
[ User UI ] <──( Context + Citations )── [ LanceDB Embedded ]
                                        (Ollama Local Inference)
```

## 🛠️ Production Tech Stack

*   **Frontend UI:** **Next.js 15 (React)**, TypeScript, Tailwind CSS, Axios.
*   **AI Engine Backend:** **FastAPI (Python)**, Uvicorn asynchronous server.
*   **Orchestration Layer:** **LangChain**, `langchain-ollama`.
*   **Vector Compute (On-Disk):** **LanceDB** (Embedded, serverless columnar file structure).
*   **Local AI Models:** `nomic-embed-text` (Embeddings) & `llama3.2:3b` (Inference).

## 🚀 Key Architectural Highlights

*   **Zero-Cloud Cost Design:** Fully operational via local hardware acceleration through Ollama integration, bypassing cloud API expenditures (OpEx).
*   **Data Sovereignty & Privacy:** Operational documents never leave the host server framework. Text extractions, vector transformations, and inferences happen 100% locally.
*   **Hallucination Defenses:** Custom, rigid context-injection system prompting rules prevent the LLM from synthesizing information outside the indexed document bounds.
*   **Page-Level Citations:** Extracts exact original metadata parameters from input matrices, appending human-readable PDF source names and page tracking arrays to user streams.

## 🔧 Installation & Local Setup

### Prerequisites
Ensure you have [Node.js v20+](https://nodejs.org), [Python 3.10+](https://python.org), and [Ollama](https://ollama.com) installed.

### 1. Model Initialization
Download the lightweight open-source data weights to your local machine environment:
```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # Or 'venv\Scripts\activate' on Windows
pip install -r requirements.txt
python main.py
```

### 3. Frontend Setup
```bash
cd ../frontend
npm install
npm run dev
```
Open **`http://localhost:3000/admin`** to drop in your first corporate manual, then switch to **`http://localhost:3000/chat`** to prompt the local AI model network.