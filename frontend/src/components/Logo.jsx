import { UtensilsCrossed } from "lucide-react";

export function Logo({ compact = false, className = "", src = "", alt = "Logo" }) {
  // When a restaurant logo URL is provided, render it (aspect ratio preserved).
  if (src) {
    return (
      <div className={`flex items-center gap-2 ${className}`} data-testid="restaurant-logo">
        <img
          src={src}
          alt={alt}
          className="h-9 w-auto max-w-[180px] rounded-lg object-contain"
          onError={(e) => { e.currentTarget.style.display = "none"; }}
        />
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${className}`} data-testid="upxero-logo">
      <span className="grid h-8 w-8 place-items-center rounded-lg bg-emerald-600 text-white shadow-sm">
        <UtensilsCrossed className="h-4.5 w-4.5" size={18} />
      </span>
      {!compact && (
        <span className="font-heading text-lg font-bold tracking-tight text-slate-900">
          Upxero<span className="text-emerald-600"> Ordering</span>
        </span>
      )}
    </div>
  );
}
