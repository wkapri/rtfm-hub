import { categoryIcon } from "./categoryIcon";
import { BoxIcon } from "./Icons";
import type { Product } from "./types";

interface Props {
  products: Product[];
  onSelect: (product: Product) => void;
  onAdd: () => void;
}

export default function ProductList({ products, onSelect, onAdd }: Props) {
  if (products.length === 0) {
    return (
      <div className="empty-state">
        <BoxIcon size={44} />
        <div>
          <p className="empty-state-title">No products yet</p>
          <p className="empty-state-hint">
            Add the things you own — appliances, vehicles, electronics — to keep track of
            manuals, warranties, and maintenance in one place.
          </p>
        </div>
        <button className="button primary" onClick={onAdd}>
          Add your first product
        </button>
      </div>
    );
  }

  return (
    <div className="content">
      <div className="product-grid">
        {products.map((p) => (
          <button key={p.id} className="product-card" onClick={() => onSelect(p)}>
            <div className="product-card-top">
              <span className="product-icon" aria-hidden="true">
                {categoryIcon(p.category)}
              </span>
              <div style={{ minWidth: 0 }}>
                <p className="product-card-nickname">{p.nickname}</p>
                {(p.brand || p.model) && (
                  <p className="product-card-meta">
                    {[p.brand, p.model].filter(Boolean).join(" ")}
                    {p.year ? ` · ${p.year}` : ""}
                  </p>
                )}
              </div>
            </div>
            <div className="badge-row">
              {p.category && <span className="badge">{p.category}</span>}
              <WarrantyBadge expires={p.warranty_expires} />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function WarrantyBadge({ expires }: { expires: string | null }) {
  if (!expires) return null;
  const daysLeft = Math.floor((new Date(expires).getTime() - Date.now()) / 86_400_000);
  if (daysLeft < 0) return <span className="badge danger">Warranty expired</span>;
  if (daysLeft < 60) return <span className="badge warning">Warranty ends soon</span>;
  return <span className="badge">Under warranty</span>;
}
