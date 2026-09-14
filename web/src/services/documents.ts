export type DocumentStatus = "uploading" | "parsing" | "indexing" | "ready" | "failed";

export type RagDocument = {
  id: string;
  name: string;
  file_hash: string;
  mime_type: string;
  size: number;
  status: DocumentStatus;
  error_message: string | null;
  version: number;
  permission_tags: string[];
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentListResponse = {
  items: RagDocument[];
  total: number;
  page: number;
  page_size: number;
};

const apiUrl = import.meta.env.VITE_SSW_API_URL || "http://127.0.0.1:8000";

async function responseError(response: Response, fallback: string): Promise<Error> {
  try {
    const payload = await response.json() as { detail?: unknown; message?: unknown };
    if (typeof payload.detail === "string") {
      return new Error(payload.detail);
    }
    if (typeof payload.message === "string") {
      return new Error(payload.message);
    }
  } catch {
    // 非 JSON 错误响应使用统一提示。
  }
  return new Error(`${fallback}：${response.status}`);
}

export async function listDocuments(
  page = 1,
  pageSize = 20,
  status?: DocumentStatus,
): Promise<DocumentListResponse> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status) {
    params.set("status", status);
  }

  const response = await fetch(`${apiUrl}/documents?${params.toString()}`);
  if (!response.ok) {
    throw await responseError(response, "加载文档失败");
  }
  return await response.json() as DocumentListResponse;
}

export async function uploadDocument(file: File): Promise<RagDocument> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${apiUrl}/documents`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw await responseError(response, "上传文档失败");
  }
  return await response.json() as RagDocument;
}

export async function retryDocument(documentId: string): Promise<RagDocument> {
  const response = await fetch(`${apiUrl}/documents/${documentId}/retry`, {
    method: "POST",
  });
  if (!response.ok) {
    throw await responseError(response, "重试文档失败");
  }
  return await response.json() as RagDocument;
}

export async function deleteDocument(documentId: string): Promise<void> {
  const response = await fetch(`${apiUrl}/documents/${documentId}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw await responseError(response, "删除文档失败");
  }
}
