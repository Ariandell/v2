/**
 * useAuth — Google OAuth user state management.
 * Handles login, logout, and persistence to localStorage.
 */

import { useState } from "react";
import { jwtDecode } from "jwt-decode";
import type { UserInfo } from "../types";

export function useAuth() {
  const [user, setUser] = useState<UserInfo | null>(() => {
    try {
      const saved = localStorage.getItem("user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const handleLoginSuccess = (credentialResponse: any) => {
    try {
      const decoded: any = jwtDecode(credentialResponse.credential);
      const userInfo: UserInfo = {
        name: decoded.name,
        email: decoded.email,
        picture: decoded.picture,
      };
      setUser(userInfo);
      localStorage.setItem("user", JSON.stringify(userInfo));
    } catch (err) {
      console.error("Login decoding failed:", err);
    }
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem("user");
  };

  return { user, handleLoginSuccess, handleLogout };
}
