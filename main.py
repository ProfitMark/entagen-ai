
import os
import asyncio
import uuid
import datetime
import mimetypes
from base64 import b64encode
from typing import List, Optional

from fastapi import FastAPI, Request, HTTPException, status, UploadFile, File, Header, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

import google.generativeai as genai
from google.cloud import firestore

# --- Environment Configuration ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set. Please set it for Gemini AI operations.")

# --- Firestore Initialization ---
try:
    db = firestore.Client()
    documents_collection_ref = db.collection("documents")
    users_collection_ref = db.collection("users") # New: Users collection
    print("Firestore client initialized successfully.")
except Exception as e:
    print(f"Error initializing Firestore client: {e}")
    # For local dev, ensure GOOGLE_APPLICATION_CREDENTIALS is set if not using gcloud auth.

# --- Gemini AI Configuration ---
genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL_NAME = 'gemini-2.5-flash-preview'

# --- Pydantic Models ---
class DocumentStatus(str, BaseModel):
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'

class Document(BaseModel):
    id: str
    name: str
    summary: Optional[str] = None
    status: DocumentStatus
    timestamp: datetime.datetime
    user_id: str # New: Link document to a user

class AnalyzeDocumentResponse(BaseModel):
    summary: Optional[str] = None
    status: DocumentStatus
    documentId: str

# New Pydantic models for user registration
class UserRegistrationRequest(BaseModel):
    email: EmailStr

class UserResponse(BaseModel):
    id: str # For simplicity, the ID is the email itself
    email: EmailStr

# --- FastAPI Dependencies ---
async def get_current_user_id(x_user_id: Optional[str] = Header(None)) -> str:
    """Dependency to extract user ID from X-User-Id header."""
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Изисква се X-User-Id хедър за автентикация."
        )
    return x_user_id

# --- Document Processing Service ---
class DocumentService:
    def __init__(self, gemini_model_name: str, documents_collection: firestore.CollectionReference, users_collection: firestore.CollectionReference):
        self._gemini_model_name = gemini_model_name
        self._documents_collection = documents_collection
        self._users_collection = users_collection # New: Users collection reference
        self._gemini_model = genai.GenerativeModel(self._gemini_model_name)

    async def register_or_get_user(self, email: EmailStr) -> UserResponse:
        """Registers a new user or returns an existing one by email."""
        user_ref = self._users_collection.document(email) # Using email as document ID
        user_doc = user_ref.get()

        if user_doc.exists:
            print(f"Потребител {email} вече съществува.")
            return UserResponse(id=email, email=email)
        else:
            user_data = {
                "email": email,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            user_ref.set(user_data)
            print(f"Нов потребител регистриран: {email}")
            return UserResponse(id=email, email=email)

    async def save_document_to_firestore(self, document_id: str, name: str, summary: Optional[str], status: DocumentStatus, user_id: str):
        """Saves or updates a document entry in Firestore, linked to a user."""
        doc_data = {
            "name": name,
            "summary": summary,
            "status": status.value,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "user_id": user_id, # New: Store user ID with the document
        }
        self._documents_collection.document(document_id).set(doc_data)
        print(f"Документ '{name}' ({document_id}) записан за потребител '{user_id}' във Firestore със статус: {status.value}")

    async def get_document_from_firestore(self, document_id: str, user_id: str) -> Optional[Document]:
        """Fetches a single document from Firestore by ID, ensuring it belongs to the user."""
        doc_ref = self._documents_collection.document(document_id)
        doc = doc_ref.get()
        if doc.exists:
            doc_data = doc.to_dict()
            if doc_data.get("user_id") != user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нямате разрешение да достъпвате този документ.")
            timestamp_dt = datetime.datetime.fromisoformat(doc_data.get("timestamp"))
            return Document(
                id=doc.id,
                name=doc_data.get("name"),
                summary=doc_data.get("summary"),
                status=DocumentStatus(doc_data.get("status", DocumentStatus.PENDING.value)),
                timestamp=timestamp_dt,
                user_id=doc_data.get("user_id") # Include user_id in the response
            )
        return None

    async def get_document_history_from_firestore(self, user_id: str) -> List[Document]:
        """Fetches all analyzed documents for a specific user from Firestore, ordered by timestamp."""
        docs_stream = self._documents_collection.where("user_id", "==", user_id).order_by("timestamp", direction=firestore.Query.DESCENDING).stream()
        history = []
        for doc in docs_stream:
            doc_data = doc.to_dict()
            timestamp_dt = datetime.datetime.fromisoformat(doc_data.get("timestamp"))
            history.append(Document(
                id=doc.id,
                name=doc_data.get("name"),
                summary=doc_data.get("summary"),
                status=DocumentStatus(doc_data.get("status", DocumentStatus.PENDING.value)),
                timestamp=timestamp_dt,
                user_id=doc_data.get("user_id")
            ))
        return history

    async def _process_file_with_gemini(self, file_content_bytes: bytes, mime_type: str) -> str:
        """Sends file content to Gemini for analysis and returns the summary."""
        prompt_text = "Обобщи този документ на български език, като извлечеш основните точки, цели и ключови заключения. Бъди подробен, но и кратък."

        try:
            file_part = genai.upload_file(file_content_bytes, mime_type=mime_type)
            contents = [prompt_text, file_part]

            response = await self._gemini_model.generate_content(
                contents,
                config={
                    "temperature": 0.3,
                    "topK": 32,
                    "topP": 0.8,
                },
                request_options={"timeout": 600}
            )

            summary = response.text
            if not summary:
                raise ValueError("Gemini AI не върна обобщение.")
            
            genai.delete_file(file_part.name)
            
            return summary
        except genai.types.BrokenGenerationError as e:
            print(f"Gemini AI генерацията се счупи: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gemini AI не успя да генерира съдържание. Вероятно съдържанието е неподходящо или твърде голямо. Грешка: {str(e)}"
            )
        except Exception as e:
            print(f"Грешка при извикване на Gemini AI: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Грешка при обработка на документа с AI: {str(e)}"
            )

    async def analyze_document(self, file: UploadFile, user_id: str) -> AnalyzeDocumentResponse:
        """Handles the full document analysis workflow, linking to a user."""
        document_id = str(uuid.uuid4())
        file_name = file.filename or "Неизвестен документ"
        
        mime_type = file.content_type if file.content_type and file.content_type != "application/octet-stream" \
            else mimetypes.guess_type(file_name)[0] or "application/octet-stream"

        if not mime_type or mime_type == "application/octet-stream":
             print(f"Предупреждение: Неизвестен MIME тип за файла '{file_name}'. Опит за обработка като текст/обикновен текст.")
             mime_type = "text/plain"

        # 1. Initial save to Firestore as PENDING
        await self.save_document_to_firestore(document_id, file_name, None, DocumentStatus.PENDING, user_id)

        try:
            file_content = await file.read()
            # 2. Process with Gemini AI
            summary = await self._process_file_with_gemini(file_content, mime_type)

            # 3. Update Firestore with COMPLETED status and summary
            await self.save_document_to_firestore(document_id, file_name, summary, DocumentStatus.COMPLETED, user_id)

            return AnalyzeDocumentResponse(documentId=document_id, summary=summary, status=DocumentStatus.COMPLETED)
        except HTTPException:
            await self.save_document_to_firestore(document_id, file_name, None, DocumentStatus.FAILED, user_id)
            raise
        except Exception as e:
            await self.save_document_to_firestore(document_id, file_name, None, DocumentStatus.FAILED, user_id)
            print(f"Неочаквана грешка по време на анализ на документа '{file_name}' ({document_id}) за потребител '{user_id}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Неочаквана грешка при анализ на документа: {str(e)}"
            )

# --- FastAPI App Initialization ---
app = FastAPI(
    title="EntaGen API",
    description="Backend за EntaGen - инструмент за анализ на корпоративни документи с Gemini AI.",
    version="1.0.0",
)

# --- CORS Middleware ---
# For development, allow all origins. In a real production setup, origins should be restricted to known frontend URLs.
origins = ["*"] 

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], # Allow X-User-Id header
)

# --- Global Exception Handlers ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handles custom HTTP exceptions, returning a JSON response."""
    print(f"HTTP Грешка: {exc.status_code} - {exc.detail} (URL: {request.url})")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handles generic Python exceptions, returning a 500 JSON response."""
    import traceback
    traceback.print_exc()
    print(f"Неочаквана сървърна грешка: {exc} (URL: {request.url})")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Възникна непредвидена грешка на сървъра. Моля, опитайте отново по-късно."},
    )

# Initialize DocumentService with both collections
document_service = DocumentService(GEMINI_MODEL_NAME, documents_collection_ref, users_collection_ref)

# --- Frontend Serving ---
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- API Routes ---

# User management endpoint
@app.post("/users/register", response_model=UserResponse, summary="Регистрация / Вход на потребител",
          description="Регистрира нов потребител или връща съществуващ по имейл адрес. Имейлът служи като потребителски ID.")
async def register_user_endpoint(request: UserRegistrationRequest):
    return await document_service.register_or_get_user(request.email)

@app.post("/documents/analyze", response_model=AnalyzeDocumentResponse, summary="Анализиране на нов документ",
          description="Качва и анализира нов документ, използвайки Gemini AI, асоциирайки го с текущия потребител.")
async def analyze_document_endpoint(file: UploadFile = File(...), current_user_id: str = Depends(get_current_user_id)):
    return await document_service.analyze_document(file, current_user_id)

@app.get("/documents/history", response_model=List[Document], summary="История на документи",
         description="Връща списък с всички анализирани документи за текущия потребител, подредени по дата на създаване.")
async def get_document_history_endpoint(current_user_id: str = Depends(get_current_user_id)):
    return await document_service.get_document_history_from_firestore(current_user_id)

@app.get("/documents/{document_id}", response_model=Document, summary="Взимане на документ по ID",
         description="Връща детайли за конкретен документ по неговото уникално ID, ако принадлежи на текущия потребител.")
async def get_document_by_id_endpoint(document_id: str, current_user_id: str = Depends(get_current_user_id)):
    document = await document_service.get_document_from_firestore(document_id, current_user_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документът не е намерен или не принадлежи на текущия потребител.")
    return document
