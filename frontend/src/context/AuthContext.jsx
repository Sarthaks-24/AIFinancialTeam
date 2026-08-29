import { createContext, useContext, useEffect, useState } from "react";
import { jwtDecode } from "jwt-decode";
import { login as loginRequest } from "../api/authApi";

const AuthContext = createContext(null);

function decodeUser(token) {
  try {
    const payload = jwtDecode(token);
    return {
      id: payload.user_id || payload.sub || null,
      username: payload.username || payload.user_name || payload.sub || "User",
      groups: payload.groups || [],
      exp: payload.exp,
    };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access");
    if (token) {
      const decoded = decodeUser(token);
      if (decoded && decoded.exp * 1000 > Date.now()) {
        setUser(decoded);
      } else {
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
      }
    }
    setLoading(false);
  }, []);

  async function login(username, password) {
    const data = await loginRequest(username, password);
    localStorage.setItem("access", data.access);
    localStorage.setItem("refresh", data.refresh);
    const decoded = decodeUser(data.access);
    setUser(decoded);
    return decoded;
  }

  function logout() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    setUser(null);
  }

  function hasRole(...roles) {
    if (!user) return false;
    if (user.groups?.includes("Admin")) return true;
    return roles.some((r) => user.groups?.includes(r));
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
