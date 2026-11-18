/*
@c3:component
name: Auth Context
container: Frontend
description: |
  - Checks the session when the app loads
  - Exposes the signed-in user and logout to the app
short_desc: React auth state — checks session on load, exposes logout
uses:
  - Auth API:
    - "checks the session"
    - "signs the user out"
    short_desc: "checks session, signs out"
    technology: REST
*/

import { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import { fetchMe, logout as apiLogout } from "../services/api";
import type { AuthUser } from "../services/api";

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isLoading: true,
  logout: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchMe()
      .then(setUser)
      .catch((err) => { console.error("fetchMe error:", err); setUser(null); })
      .finally(() => setIsLoading(false));
  }, []);

  const logout = async () => {
    await apiLogout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}
