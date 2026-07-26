import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from prompts import get_system_instruction
import lancedb

app = FastAPI(title="Enterprise Local RAG Bot API")

# --- MANDATORY CORS SECURITY CONFIGURATION ---
# Allows your Next.js web application frontend to securely communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js local development address
    allow_credentials=True,
    allow_methods=["*"],                      # Allows all actions (POST, GET, OPTIONS, etc.)
    allow_headers=["*"],                      # Allows all web transmission headers
)

# Initialize Local Vector DB and 100% Free Embedding Model
DB_DIR = "./data/lancedb_data"
os.makedirs(DB_DIR, exist_ok=True)
db = lancedb.connect(DB_DIR)

# Using nomic-embed-text running locally via Ollama
embeddings_model = OllamaEmbeddings(model="nomic-embed-text")

TABLE_NAME = "pdf_knowledge_base"

def get_or_create_table():
    if TABLE_NAME in db.table_names():
        return db.open_table(TABLE_NAME)
    return None

# --- API Data Transfer Models ---
class ChatQuery(BaseModel):
    question: str

# --- 1. ADMIN ENDPOINT: Upload, Parse, and Embed PDF Locally ---
@app.post("/admin/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    # Save uploaded file to local file system layout temporarily
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Load and parse PDF pages
        loader = PyPDFLoader(temp_path)
        docs = loader.load()
        
        # Split text into logical chunks with semantic overlap structures
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(docs)
        
        # Build local records array
        records = []
        for chunk in chunks:
            # Generate the vector embedding locally using your hardware via Ollama
            vector = embeddings_model.embed_query(chunk.page_content)
            
            records.append({
                "vector": vector,
                "text": chunk.page_content,
                "source": file.filename,
                "page": chunk.metadata.get("page", 0) + 1  # 1-indexed for human readability
            })
            
        # Write directly to serverless LanceDB file tables on disk
        if TABLE_NAME in db.table_names():
            table = db.open_table(TABLE_NAME)
            table.add(records)
        else:
            table = db.create_table(TABLE_NAME, data=records)
            
        return {
            "status": "success", 
            "message": f"Successfully processed {file.filename}", 
            "total_chunks_indexed": len(records)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Remove raw physical footprint file from application server
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- 2. USER ENDPOINT: Query, Retrieve Vectors, and Chat Locally ---
@app.post("/user/chat")
async def chat_with_docs(query: ChatQuery):
    table = get_or_create_table()
    if not table:
        raise HTTPException(status_code=404, detail="No documentation has been uploaded by an Admin yet.")
        
    try:
        # Vectorize the incoming question sequence locally
        query_vector = embeddings_model.embed_query(query.question)
        
        # Pull Top 3 closest structural reference chunks out of database
        search_results = table.search(query_vector).limit(3).to_pandas()
        
        if search_results.empty:
            return {"answer": "No relevant system context was found to answer this question.", "citations": []}
            
        # Compile contextual inputs and map human structural references
        context_str = ""
        citations = []
        
        for idx, row in search_results.iterrows():
            context_str += f"\n[Context Section {idx+1} from {row['source']}, Page {row['page']}]:\n{row['text']}\n"
            citations.append({
                "source_file": row['source'],
                "page": int(row['page'])
            })
            
        # Establish hallucination guardrails via system prompting architecture
        system_instruction = get_system_instruction(context_str)
        
        # Invoke lightweight, fast local Llama 3.2 1B model
        llm = ChatOllama(model="llama3.2:1b", temperature=0.0)
        ai_message = llm.invoke([
            ("system", system_instruction),
            ("user", query.question)
        ])
        
        return {
            "answer": ai_message.content,
            "citations": citations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Boots server locally on port 8000
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
