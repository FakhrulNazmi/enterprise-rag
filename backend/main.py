import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader  
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings, ChatOllama
from prompts import get_system_instruction
import lancedb

app = FastAPI(title="SoloRAG Core Engine API")

# --- MANDATORY CORS SECURITY CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Next.js via domain resolution
        "http://127.0.0.1:3000",   # Next.js via raw loopback IP resolution
        "http://[::1]:3000"        # Next.js via native IPv6 resolution
    ],  
    allow_credentials=True,
    allow_methods=["*"],                      
    allow_headers=["*"],                      
)

# Initialize Local Vector DB and 100% Free Embedding Model
DB_DIR = "./data/lancedb_data"
os.makedirs(DB_DIR, exist_ok=True)
db = lancedb.connect(DB_DIR)

# Using nomic-embed-text running locally via Ollama (Outputs 768 dimensions)
embeddings_model = OllamaEmbeddings(model="nomic-embed-text")

TABLE_NAME = "pdf_knowledge_base"

def get_or_create_table():
    global db
    try:
        return db.open_table(TABLE_NAME)
    except Exception:
        return None

# --- API Data Transfer Models ---
class ChatQuery(BaseModel):
    question: str

class DeleteDocRequest(BaseModel):
    filename: str

# --- 1. ADMIN ENDPOINT: Upload, Parse, and Embed PDF Locally ---
@app.post("/admin/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    temp_path = f"temp_{file.filename}"
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # High-speed synchronous PDF string scraper abstraction
        def extract_pdf_text(path):
            reader = PdfReader(path)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() or ""
            return full_text

        raw_text = await run_in_threadpool(extract_pdf_text, temp_path)
        
        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="The uploaded PDF contains no readable text layers.")
            
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_text(raw_text)
        
        records = []
        for idx, chunk_content in enumerate(texts):
            # Safe thread-bound concurrent async vectorizations
            vector = await embeddings_model.aembed_query(chunk_content)
            
            records.append({
                "vector": vector,
                "text": chunk_content,
                "source": file.filename,
                "page": 1  
            })
            
        # Multi-file dynamic safe appending strategy handler block
        try:
            table = db.open_table(TABLE_NAME)
            table.add(records)
        except Exception:
            table = db.create_table(TABLE_NAME, data=records)
            
        return {
            "status": "success", 
            "message": f"Successfully processed {file.filename}", 
            "total_chunks_indexed": len(records)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- 2. USER ENDPOINT: Query, Retrieve Vectors, and Chat Locally ---
@app.post("/user/chat")
async def chat_with_docs(query: ChatQuery):
    FALLBACK_TEXT = "I cannot find the complete details for this action in the uploaded documentation."
    
    # GUARDRAIL 1: Hard block off-topic coding / generic chat keywords immediately
    user_question_lower = query.question.lower()
    off_topic_keywords = ["javascript", "python", "html", "css", "write code", "create a function", "what you eat"]
    if any(keyword in user_question_lower for keyword in off_topic_keywords):
        return {"answer": FALLBACK_TEXT, "citations": []}

    table = get_or_create_table()
    if not table:
        return {"answer": FALLBACK_TEXT, "citations": []}
        
    try:
        query_vector = await embeddings_model.aembed_query(query.question)
        search_results = table.search(query_vector).select(["text", "source", "page"]).limit(3).to_pandas()
        
        if search_results.empty:
            return {"answer": FALLBACK_TEXT, "citations": []}
            
        context_str = ""
        citations = []
        valid_chunks_found = False
        
        for idx, row in search_results.iterrows():
            if row.get('_distance', 0) > 1.25:
                continue
                
            valid_chunks_found = True
            context_str += f"\n[Context Section {idx+1} from {row['source']}, Page {row['page']}]:\n{row['text']}\n"
            citations.append({
                "source_file": row['source'],
                "page": int(row['page'])
            })
            
        if not valid_chunks_found:
            return {"answer": FALLBACK_TEXT, "citations": []}
            
        system_instruction = get_system_instruction(context_str)
        
        llm = ChatOllama(model="llama3.2:1b", temperature=0.0)
        ai_message = await llm.ainvoke([
            ("system", system_instruction),
            ("user", query.question)
        ])
        
        return {
            "answer": ai_message.content,
            "citations": citations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 3. ADMIN ENDPOINT: List unique uploaded document files ---
@app.get("/admin/documents")
def list_documents():
    table = get_or_create_table()
    if not table:
        return {"documents": []}
        
    try:
        df = table.to_pandas()
        if df.empty:
            return {"documents": []}
            
        summary = df.groupby('source').size().reset_index(name='chunks')
        
        documents_list = []
        for _, row in summary.iterrows():
            documents_list.append({
                "filename": row['source'],
                "total_chunks": int(row['chunks'])
            })
            
        return {"documents": documents_list}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 4. ADMIN ENDPOINT: Delete a specific file's vectors ---
@app.post("/admin/delete-document")
def delete_document(payload: DeleteDocRequest):
    table = get_or_create_table()
    if not table:
        raise HTTPException(status_code=404, detail="Database table not initialized.")
        
    try:
        table.delete(f"source = '{payload.filename}'")
        return {"status": "success", "message": f"Successfully deleted all vectors for '{payload.filename}'"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove targeted records: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
