
export interface Document {
  id: string;
  name: string;
  summary: string;
  status: DocumentStatus;
  timestamp: string; // ISO 8601 string
  userId: string; // New: Link document to a user
}

export enum DocumentStatus {
  PENDING = 'PENDING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
}

export interface AnalyzeDocumentResponse {
  summary: string;
  status: DocumentStatus;
  documentId: string;
}

export interface ApiError {
  detail: string;
}

// New interfaces for user registration
export interface UserRegistrationRequest {
  email: string;
}

export interface UserResponse {
  id: string; // This will be the email itself for simplicity
  email: string;
}
