
import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import authClient from '@/lib/authClient.js';
import { toast } from 'sonner';

const AuthContext = createContext({});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(authClient.model);
  const [isAuthenticated, setIsAuthenticated] = useState(authClient.isValid);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const unsubscribe = authClient.subscribe((model) => {
      setUser(model);
      setIsAuthenticated(authClient.isValid);
    });

    authClient.initialize().finally(() => {
      if (isMounted) {
        setIsLoading(false);
      }
    });

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, []);

  const login = useCallback(async (email, password) => {
    return authClient.login(email, password);
  }, []);

  const signup = useCallback(async (email, password, name) => {
    return authClient.signup(email, password, name);
  }, []);

  const requestPasswordReset = useCallback(async (email, redirectTo) => {
    return authClient.requestPasswordReset(email, redirectTo);
  }, []);

  const preparePasswordRecovery = useCallback(async (currentUrl) => {
    return authClient.preparePasswordRecovery(currentUrl);
  }, []);

  const updatePassword = useCallback(async (password) => {
    return authClient.updatePassword(password);
  }, []);

  const logout = useCallback(async () => {
    await authClient.logout();
    toast.success('Desconectado com sucesso!');
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoading,
        login,
        signup,
        requestPasswordReset,
        preparePasswordRecovery,
        updatePassword,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
