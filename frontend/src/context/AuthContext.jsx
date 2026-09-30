import { createContext, useCallback, useContext, useEffect, useState } from "react";
import api from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined); // undefined=loading, null=not auth
  const [restaurant, setRestaurant] = useState(null);

  const loadMe = async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data.user);
      setRestaurant(data.restaurant || null);
    } catch {
      setUser(null);
      setRestaurant(null);
    }
  };

  useEffect(() => {
    loadMe();
  }, []);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    setUser(data.user);
    await loadMe();
    return data.user;
  };

  const register = async (payload) => {
    const { data } = await api.post("/auth/register", payload);
    setUser(data.user);
    await loadMe();
    return data.user;
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      /* ignore */
    }
    setUser(null);
    setRestaurant(null);
  };

  return (
    <AuthContext.Provider
      value={{ user, restaurant, setRestaurant, login, register, logout, refetch: loadMe }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
