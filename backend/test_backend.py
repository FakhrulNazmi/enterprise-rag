import os
import pytest
from fastapi.testclient import TestClient
import lancedb

# Force test configuration before importing your main app
os.environ["LANCEDB_TEST_MODE"] = "true"

import main
from main import app, TABLE_NAME

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Safely cleans up testing storage instances using try/except checks."""
    try:
        main.db.drop_table(TABLE_NAME)
    except Exception:
        pass
        
    yield
    
    try:
        main.db.drop_table(TABLE_NAME)
    except Exception:
        pass
        
    main.db = lancedb.connect(main.DB_DIR)

def test_chat_without_documents_returns_404():
    """Ensures user endpoint fails gracefully if no files are uploaded yet."""
    response = client.post("/user/chat", json={"question": "What is the policy?"})
    assert response.status_code == 404
    assert response.json()["detail"] == "No documentation has been uploaded by an Admin yet."

def test_guardrail_blocks_off_topic_questions():
    """Verifies that Guardrail 1 correctly intercepts out-of-scope code requests."""
    main.db.create_table(
        TABLE_NAME, 
        data=[{"vector": [0.0]*768, "text": "test", "source": "test.pdf", "page": 1}],
        mode="overwrite"
    )
    
    response = client.post("/user/chat", json={"question": "how to write a javascript function"})
    assert response.status_code == 200
    assert response.json()["answer"] == "I cannot find the complete details for this action in the uploaded documentation."

def test_list_documents_empty_and_populated():
    """Tests the document registry directory tracking mechanics."""
    response = client.get("/admin/documents")
    assert response.status_code == 200
    assert response.json() == {"documents": []}
    
    mock_data = [
        {"vector": [0.1]*768, "text": "Chunk 1 content", "source": "manual_v1.pdf", "page": 1},
        {"vector": [0.2]*768, "text": "Chunk 2 content", "source": "manual_v1.pdf", "page": 2}
    ]
    main.db.create_table(TABLE_NAME, data=mock_data, mode="overwrite")
    
    response = client.get("/admin/documents")
    assert response.status_code == 200
    docs = response.json()["documents"]
    
    assert len(docs) == 1
    assert docs[0]["filename"] == "manual_v1.pdf"
    assert docs[0]["total_chunks"] == 2

def test_delete_specific_document():
    """Validates that targeted row deletion drops targeted files without breaking others."""
    mock_data = [
        {"vector": [0.1]*768, "text": "A", "source": "keep_me.pdf", "page": 1},
        {"vector": [0.2]*768, "text": "B", "source": "delete_me.pdf", "page": 1}
    ]
    main.db.create_table(TABLE_NAME, data=mock_data, mode="overwrite")
    
    response = client.post("/admin/delete-document", json={"filename": "delete_me.pdf"})
    assert response.status_code == 200
    assert "Successfully deleted" in response.json()["message"]
    
    # Verify only keep_me.pdf remains intact
    remaining_docs = client.get("/admin/documents").json()["documents"]
    assert len(remaining_docs) == 1
    assert remaining_docs[0]["filename"] == "keep_me.pdf"
