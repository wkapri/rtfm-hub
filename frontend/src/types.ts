export interface Product {
  id: string;
  nickname: string;
  brand: string | null;
  model: string | null;
  category: string | null;
  year: number | null;
  purchase_date: string | null;
  warranty_expires: string | null;
  notes: string | null;
  ha_device_id: string | null;
  created_at: string;
}

export interface ProductInput {
  nickname: string;
  brand: string | null;
  model: string | null;
  category: string | null;
  year: number | null;
  purchase_date: string | null;
  warranty_expires: string | null;
  notes: string | null;
}

export interface ProductDocument {
  id: string;
  product_id: string;
  document_id: string;
  document_kind: string;
  source_url: string | null;
  added_at: string;
}

export interface Document {
  id: string;
  filename: string;
  title: string;
}

export interface MaintenanceEntry {
  id: string;
  product_id: string;
  date: string;
  description: string;
  cost: string | null;
  created_at: string;
}
