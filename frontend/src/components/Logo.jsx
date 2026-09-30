import { UtensilsCrossed } from "lucide-react";

export function Logo({ compact = false, className = "" }) {
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
