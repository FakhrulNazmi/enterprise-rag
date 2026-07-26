import os
import pytest
from fastapi.testclient import TestClient
import lancedb

os.environ["LANCEDB_TEST_MODE"] = "true"

import main
from main import app, TABLE_NAME

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Forces clean isolated state layers for table arrays between runtime tests."""
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
    response = client.post("/user/chat", json={"question": "What is the policy?"})
    assert response.status_code == 200

def test_guardrail_blocks_off_topic_questions():
    main.db.create_table(
        TABLE_NAME, 
        data=[{"vector": [0.0]*768, "text": "test", "source": "test.pdf", "page": 1}],
        mode="overwrite"
    )
    response = client.post("/user/chat", json={"question": "how to write a javascript function"})
    assert response.status_code == 200
    assert "I cannot find the complete details" in response.json()["answer"]

def test_list_documents_empty_and_populated():
    response = client.get("/admin/documents")
    assert response.status_code == 200
    assert response.json() == {"documents": []}
    
    mock_data = [
        {"vector": [0.1]*768, "text": "Content", "source": "manual_v1.pdf", "page": 1}
    ]
    main.db.create_table(TABLE_NAME, data=mock_data, mode="overwrite")
    
    response = client.get("/admin/documents")
    assert response.status_code == 200
    assert response.json()["documents"][0]["filename"] == "manual_v1.pdf"

def test_delete_specific_document():
    mock_data = [
        {"vector": [0.1]*768, "text": "A", "source": "keep_me.pdf", "page": 1},
        {"vector": [0.2]*768, "text": "B", "source": "delete_me.pdf", "page": 1}
    ]
    main.db.create_table(TABLE_NAME, data=mock_data, mode="overwrite")
    
    response = client.post("/admin/delete-document", json={"filename": "delete_me.pdf"})
    assert response.status_code == 200
    
    remaining = client.get("/admin/documents").json()["documents"]
    assert len(remaining) == 1
    assert remaining[0]["filename"] == "keep_me.pdf"
