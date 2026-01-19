import os
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google.cloud import firestore
import google.generativeai as genai

# --- Configuration & Security ---
PROJECT_ID = "gen-lang-client-0119314757"
# Now securely pulling from Cloud Run Environment Variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in environment variables.")

# Initialize Gemini 1.5 Flash (Multimodal)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Initialize Firestore
db = firestore.Client(project=PROJECT_ID)

app = FastAPI(title="EntaGen Enterprise")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard: Displays documents and handles actions."""
    docs = db.collection("documents").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(15).stream()
    
    doc_rows = ""
    for d in docs:
        data = d.to_dict()
        doc_id = d.id  # Firestore document ID
        
        doc_rows += f"""
        <div class="card">
            <div class="card-header">
                <strong>{data.get('name')}</strong> 
                <span class="badge">{data.get('status')}</span>
                <small>{data.get('timestamp').strftime('%Y-%m-%d %H:%M')}</small>
            </div>
            <div class="card-body">
                <p>{data.get('summary')}</p>
                <form action="/delete/{doc_id}" method="post" style="margin:0;">
                    <button type="submit" class="btn-delete">Delete</button>
                </form>
            </div>
        </div>
        """

    return f"""
    <html>
        <head>
            <title>EntaGen Dashboard</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css">
            <style>
                .card {{ border: 1px solid #444; margin-bottom: 20px; padding: 15px; border-radius: 8px; position: relative; }}
                .badge {{ background: #2ecc71; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; }}
                .upload-section {{ background: #222; padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px dashed #555; }}
                .btn-delete {{ 
                    background-color: #ff4c4c; 
                    color: white; 
                    border: none; 
                    padding: 5px 10px; 
                    font-size: 0.8em; 
                    cursor: pointer;
                    border-radius: 4px;
                }}
                .btn-delete:hover {{ background-color: #cc0000; }}
            </style>
        </head>
        <body>
            <h1>EntaGen AI Processor</h1>
            
            <div class="upload-section">
                <h3>New Analysis</h3>
                <form action="/upload" method="post" enctype="multipart/form-data">
                    <input type="file" name="file" accept=".pdf,.txt" required>
                    <button type="submit">Upload & Summarize (BG)</button>
                </form>
            </div>

            <h2>Document History</h2>
            <div id="results">{doc_rows if doc_rows else "<p>No documents processed yet.</p>"}</div>
        </body>
    </html>
    """

@app.post("/upload")
async def handle_upload(file: UploadFile = File(...)):
    """Processes upload using Gemini's native multimodal support."""
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured.")

    try:
        content = await file.read()
        
        # Prepare document for Gemini (Direct Bytes)
        doc_part = {
            "mime_type": file.content_type,
            "data": content
        }
        
        prompt = "Моля, направи кратко резюме на този документ на български език, като подчертаеш най-важните точки."
        
        # Generation
        response = model.generate_content([prompt, doc_part])
        summary_text = response.text

        # Firestore Store
        db.collection("documents").add({
            "name": file.filename,
            "summary": summary_text,
            "status": "completed",
            "timestamp": datetime.utcnow()
        })

        return RedirectResponse(url="/", status_code=303)

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Processing failed.")

@app.post("/delete/{doc_id}")
async def delete_document(doc_id: str):
    """Deletes a document from Firestore."""
    try:
        db.collection("documents").document(doc_id).delete()
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        print(f"Delete Error: {e}")
        raise HTTPException(status_code=500, detail="Delete failed.")
        
