// src/admin/types.ts
// Backend schemas.py ile birebir eşleşen TypeScript tipleri

export type JobStatus = 'pending' | 'running' | 'done' | 'failed' | 'canceled';

export interface Article {
  no: string;
  baslik: string;
  metin: string;
  alt_baslik?: string | null;
  duplicate_lines_removed?: number;
}

export interface RawData {
  law_id: string;
  law_name: string;
  url: string;
  scraped_at: string;
  articles: Article[];
}

export interface CleanData {
  law_id: string;
  law_name: string;
  preprocessed_at?: string;
  cleaned_at?: string;
  article_count?: number;
  duplicate_lines_removed?: number;
  dropped_article_count?: number;
  dropped_article_nos?: string[];
  articles: Article[];
}

export interface JobRecord {
  id: string;
  law_id: string;
  law_name: string;
  status: JobStatus;
  raw_path: string | null;
  clean_path: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
  parent_job_id?: string | null;
  raw_data?: RawData | null;
  clean_data?: CleanData | null;
}

export interface ScrapeRequest {
  law_id: string;
  law_name: string;
  url?: string;       // opsiyonel — boşsa backend otomatik türetir
  tur?: string;       // varsayılan: "1" (Kanun)
  tertip?: string;    // varsayılan: "5"
}

export interface ScrapeResponse {
  job_id: string;
  status: JobStatus;
  message: string;
}

export interface PreprocessResponse {
  job_id: string;
  status: JobStatus;
  clean_path: string | null;
  article_count: number | null;
  duplicate_lines_removed?: number | null;
}

export interface DocumentRecord {
  id: string;
  filename: string;
  file_type: 'pdf' | 'docx' | 'txt';
  status: 'processing' | 'indexed' | 'failed';
  chunk_count: number;
  document_id: string;
  created_at: string;
  updated_at: string;
  error: string | null;
}

export interface DocumentUploadResponse {
  id: string;
  document_id: string;
  filename: string;
  file_type: string;
  status: string;
  message: string;
}

export interface ChunkRecord {
  chunk_index: number;
  chunk_text: string;
  char_count: number;
  start_char: number | null;
  end_char: number | null;
  manually_edited: boolean;
}

export interface ChunksResponse {
  doc_id: string;
  filename: string;
  total: number;
  limit: number;
  offset: number;
  pages: number;
  has_offsets: boolean;
  chunks: ChunkRecord[];
}

export interface BoundaryShiftRequest {
  boundary_index: number;
  new_offset: number;
}

export interface BoundaryShiftResponse {
  status: string;
  boundary_index: number;
  new_offset: number;
  chunks: [ChunkRecord, ChunkRecord];
}
