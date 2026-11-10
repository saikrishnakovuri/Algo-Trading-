from fastapi import APIRouter, HTTPException, Query
import os
import glob

router = APIRouter(prefix="/api/docs", tags=["docs"])

DOCS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

@router.get("/list")
def list_docs():
    # List all .md files in root
    files = glob.glob(os.path.join(DOCS_DIR, "*.md"))
    return {"docs": [os.path.basename(f) for f in files]}

@router.get("/{name}")
def get_doc(name: str):
    if not name.endswith('.md'):
        name += '.md'
    file_path = os.path.join(DOCS_DIR, name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return {"name": name, "content": content}

@router.get("/search")
def search_docs(q: str = Query(...)):
    results = []
    files = glob.glob(os.path.join(DOCS_DIR, "*.md"))
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as doc:
                content = doc.read()
                if q.lower() in content.lower():
                    results.append({
                        "name": os.path.basename(f),
                        "snippet": content[content.lower().find(q.lower()):][:100] + "..."
                    })
        except:
            pass
    return {"results": results}
