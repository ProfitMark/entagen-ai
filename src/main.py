from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from google.cloud import firestore
import os
import uvicorn

app = FastAPI()
db = firestore.Client()

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
        <head>
            <title>EntaGen Dashboard</title>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: sans-serif; padding: 40px; background: #f4f7f6;">
            <div style="max-width: 800px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h1 style="color: #2c3e50;">EntaGen Documents</h1>
                <hr>
                <div id="data">Зареждане на документи...</div>
            </div>
            <script>
                fetch('/documents')
                    .then(res => res.json())
                    .then(data => {
                        const container = document.getElementById('data');
                        if (data.length === 0) {
                            container.innerHTML = "<p>Няма намерени документи.</p>";
                            return;
                        }
                        container.innerHTML = data.map(d => `
                            <div style="border-bottom: 1px solid #eee; padding: 15px 0;">
                                <h3 style="margin: 0; color: #3498db;">${d.name || 'Няма име'}</h3>
                                <p style="margin: 5px 0; color: #7f8c8d;">${d.summary || 'Няма резюме'}</p>
                                <span style="font-size: 12px; background: #e1f5fe; padding: 2px 8px; border-radius: 10px;">Статус: ${d.status}</span>
                            </div>
                        `).join('');
                    })
                    .catch(err => {
                        document.getElementById('data').innerHTML = "Грешка при зареждане на данните.";
                    });
            </script>
        </body>
    </html>
    """

@app.get("/documents")
def get_documents():
    docs_ref = db.collection("documents")
    docs = docs_ref.stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    # Cloud Run изисква портът да се чете от променливата PORT
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
