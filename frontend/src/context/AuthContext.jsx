import React, { createContext, useContext, useState } from "react";

// Keeps the logged in user + JWT token, so any page can ask "who is logged in?".
// The login request itself is made in authService.js; this only stores the result
// in localStorage so a page refresh does not log you out.

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const savedUser = localStorage.getItem("lpds_user");
  const [user, setUser] = useState(savedUser ? JSON.parse(savedUser) : null);

  function login(userData, token) {
    setUser(userData);
    localStorage.setItem("lpds_user", JSON.stringify(userData));
    localStorage.setItem("lpds_token", token);
  }

  function logout() {
    setUser(null);
    localStorage.removeItem("lpds_user");
    localStorage.removeItem("lpds_token");
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
