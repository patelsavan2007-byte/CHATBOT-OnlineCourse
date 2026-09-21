/**
 * ProtectedRoute — wraps routes requiring authentication.
 * Redirects to login with state so user can return after auth.
 * adminOnly flag redirects non-admin users to /chat.
 */
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext.jsx";

export default function ProtectedRoute({ children, adminOnly = false }) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (adminOnly && user.role !== "admin") {
    return <Navigate to="/chat" replace />;
  }

  return children;
}
