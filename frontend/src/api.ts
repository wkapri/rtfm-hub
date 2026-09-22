import type {
  ApproveResult,
  Candidate,
  Document,
  DiscoverResult,
  Identification,
  MaintenanceEntry,
  Product,
  ProductDocument,
  ProductInput,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: init?.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : undefined,
    ...init,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request to ${path} failed (${response.status})`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const api = {
  listProducts: () => request<Product[]>("/api/products"),
  getProduct: (id: string) => request<Product>(`/api/products/${id}`),
  createProduct: (input: ProductInput) =>
    request<Product>("/api/products", { method: "POST", body: JSON.stringify(input) }),
  identifyProduct: (description: string) =>
    request<Identification>("/api/products/identify", {
      method: "POST",
      body: JSON.stringify({ description }),
    }),
  updateProduct: (id: string, input: Partial<ProductInput>) =>
    request<Product>(`/api/products/${id}`, { method: "PATCH", body: JSON.stringify(input) }),
  deleteProduct: (id: string) => request<void>(`/api/products/${id}`, { method: "DELETE" }),

  listDocuments: () => request<Document[]>("/api/documents"),
  listProductDocuments: (productId: string) =>
    request<ProductDocument[]>(`/api/products/${productId}/documents`),
  linkDocument: (productId: string, documentId: string, kind: string) =>
    request<ProductDocument>(`/api/products/${productId}/documents`, {
      method: "POST",
      body: JSON.stringify({ document_id: documentId, document_kind: kind }),
    }),
  uploadDocument: (productId: string, file: File, kind: string) => {
    const form = new FormData();
    form.append("file", file);
    return request<ProductDocument>(
      `/api/products/${productId}/documents/upload?document_kind=${encodeURIComponent(kind)}`,
      { method: "POST", body: form },
    );
  },

  listMaintenance: (productId: string) =>
    request<MaintenanceEntry[]>(`/api/products/${productId}/maintenance`),
  addMaintenance: (productId: string, entry: { date: string; description: string; cost: number | null }) =>
    request<MaintenanceEntry>(`/api/products/${productId}/maintenance`, {
      method: "POST",
      body: JSON.stringify(entry),
    }),

  discoverManual: (productId: string) => request<DiscoverResult>(`/api/products/${productId}/discover`),
  approveCandidate: (productId: string, candidate: Candidate, kind: string) =>
    request<ApproveResult>(`/api/products/${productId}/discover/approve`, {
      method: "POST",
      body: JSON.stringify({ url: candidate.url, title: candidate.title, document_kind: kind }),
    }),
};
