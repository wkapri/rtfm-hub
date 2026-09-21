import { useEffect, useState } from "react";
import { api } from "./api";
import { PlusIcon } from "./Icons";
import ProductDetail from "./ProductDetail";
import ProductForm from "./ProductForm";
import ProductList from "./ProductList";
import type { Product } from "./types";

export default function App() {
  const [products, setProducts] = useState<Product[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    refresh();
  }, []);

  function refresh() {
    api
      .listProducts()
      .then(setProducts)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load products."));
  }

  const selected = products?.find((p) => p.id === selectedId) ?? null;

  return (
    <div className="app">
      <header className="header">
        <div className="header-titles">
          <h1 className="header-title">rtfm-hub</h1>
        </div>
        {!selected && (
          <button className="icon-button primary" onClick={() => setShowForm(true)} aria-label="Add product">
            <PlusIcon />
          </button>
        )}
      </header>

      {error && <p className="form-error" style={{ padding: 16 }}>{error}</p>}

      {products === null ? (
        <p className="loading-text">Loading…</p>
      ) : selected ? (
        <ProductDetail
          product={selected}
          onBack={() => setSelectedId(null)}
          onUpdated={(updated) => {
            setProducts((prev) => (prev ?? []).map((p) => (p.id === updated.id ? updated : p)));
          }}
          onDeleted={(id) => {
            setProducts((prev) => (prev ?? []).filter((p) => p.id !== id));
            setSelectedId(null);
          }}
        />
      ) : (
        <ProductList products={products} onSelect={(p) => setSelectedId(p.id)} onAdd={() => setShowForm(true)} />
      )}

      {showForm && (
        <ProductForm
          product={null}
          onClose={() => setShowForm(false)}
          onSaved={(created) => {
            setShowForm(false);
            setProducts((prev) => [...(prev ?? []), created]);
            setSelectedId(created.id);
          }}
        />
      )}
    </div>
  );
}
