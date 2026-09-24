import { createContext, useContext, useState, useEffect } from "react";
import { api } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("dockit_token");
    if (!token) { setLoading(false); return; }
    api.me().then(setUser).catch(() => {
      localStorage.removeItem("dockit_token");
    }).finally(() => setLoading(false));
  }, []);

  async function login(username, password) {
    const data = await api.login(username, password);
    localStorage.setItem("dockit_token", data.access_token);
    const me = await api.me();
    setUser(me);
    return me;
  }

  function logout() {
    localStorage.removeItem("dockit_token");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
