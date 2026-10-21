import { useCallback, useEffect, useState } from "react";
import api from "./api";
import { useAuth } from "../context/AuthContext";

// Owner-only billing status; staff never needs it (staff access itself requires Pro).
export function useBilling() {
  const { user } = useAuth();
  const [billing, setBilling] = useState(null);
  const load = useCallback(() => {
    if (user?.role !== "restaurant_admin") return Promise.resolve();
    return api.get("/billing/status").then(({ data }) => setBilling(data)).catch(() => setBilling(null));
  }, [user?.role]);
  useEffect(() => { load(); }, [load]);
  return { billing, isFree: billing?.plan === "free", reload: load };
}
