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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],                      
    allow_headers=["*"],                      
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
    
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        loader = PyPDFLoader(temp_path)
        docs = loader.load()
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(docs)
        
        records = []
        for chunk in chunks:
            vector = embeddings_model.embed_query(chunk.page_content)
            
            records.append({
                "vector": vector,
                "text": chunk.page_content,
                "source": file.filename,
                "page": chunk.metadata.get("page", 0) + 1  
            })
            
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
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- 2. USER ENDPOINT: Query, Retrieve Vectors, and Chat Locally ---
@app.post("/user/chat")
async def chat_with_docs(query: ChatQuery):
    # FALLBACK_TEXT is kept identical to your system prompt instruction requirements
    FALLBACK_TEXT = "I cannot find the complete details for this action in the uploaded documentation."
    
    # GUARDRAIL 1: Hard block off-topic coding / generic chat keywords immediately
    user_question_lower = query.question.lower()
    off_topic_keywords = ["javascript", "python", "html", "css", "write code", "create a function", "what you eat"]
    if any(keyword in user_question_lower for keyword in off_topic_keywords):
        return {"answer": FALLBACK_TEXT, "citations": []}

    table = get_or_create_table()
    if not table:
        raise HTTPException(status_code=404, detail="No documentation has been uploaded by an Admin yet.")
        
    try:
        query_vector = embeddings_model.embed_query(query.question)
        
        # Pull Top 3 closest structural reference chunks out of database
        # We use .select() to ensure the vector distance field ('_distance') is included
        search_results = table.search(query_vector).select(["text", "source", "page"]).limit(3).to_pandas()
        
        if search_results.empty:
            return {"answer": FALLBACK_TEXT, "citations": []}
            
        context_str = ""
        citations = []
        valid_chunks_found = False
        
        for idx, row in search_results.iterrows():
            # GUARDRAIL 2: LanceDB uses L2 (Euclidean) Distance by default.
            # A distance greater than 1.25 typically means the text is totally unrelated to the question.
            if row.get('_distance', 0) > 1.25:
                continue
                
            valid_chunks_found = True
            context_str += f"\n[Context Section {idx+1} from {row['source']}, Page {row['page']}]:\n{row['text']}\n"
            citations.append({
                "source_file": row['source'],
                "page": int(row['page'])
            })
            
        # If all retrieved chunks were poor matches, abort before hitting the LLM
        if not valid_chunks_found:
            return {"answer": FALLBACK_TEXT, "citations": []}
            
        system_instruction = get_system_instruction(context_str)
        
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
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
