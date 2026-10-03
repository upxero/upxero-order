import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { DashboardLayout } from "./components/DashboardLayout";

import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import StaffInvitation from "./pages/StaffInvitation";
import Overview from "./pages/dashboard/Overview";
import Orders from "./pages/dashboard/Orders";
import MenuItems from "./pages/dashboard/MenuItems";
import Categories from "./pages/dashboard/Categories";
import Delivery from "./pages/dashboard/Delivery";
import OpeningHours from "./pages/dashboard/OpeningHours";
import Settings from "./pages/dashboard/Settings";
import Profile from "./pages/dashboard/Profile";
import Staff from "./pages/dashboard/Staff";
import AdminRestaurants from "./pages/dashboard/AdminRestaurants";
import OrderPage from "./pages/order/OrderPage";
import OrderConfirmation from "./pages/order/OrderConfirmation";
import OrderStatus from "./pages/order/OrderStatus";
import LegalPage from "./pages/legal/LegalPage";

function App() {
  return (
    <AuthProvider>
      <Toaster position="top-right" richColors closeButton />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/registreren" element={<Register />} />
          <Route path="/wachtwoord-vergeten" element={<ForgotPassword />} />
          <Route path="/reset-wachtwoord" element={<ResetPassword />} />
          <Route path="/staff-uitnodiging" element={<StaffInvitation />} />
          <Route path="/order/:slug" element={<OrderPage />} />
          <Route path="/order-status/:token" element={<OrderStatus />} />
          <Route path="/order/:slug/bevestiging/:orderId" element={<OrderConfirmation />} />

          <Route path="/privacy" element={<LegalPage page="privacy" />} />
          <Route path="/terms" element={<LegalPage page="terms" />} />
          <Route path="/cookies" element={<LegalPage page="cookies" />} />
          <Route path="/legal" element={<LegalPage page="legal" />} />
          <Route path="/contact" element={<LegalPage page="contact" />} />

          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Overview />} />
            <Route path="bestellingen" element={<Orders />} />
            <Route path="menu" element={<MenuItems />} />
            <Route path="categorieen" element={<Categories />} />
            <Route path="bezorging" element={<Delivery />} />
            <Route path="openingstijden" element={<OpeningHours />} />
            <Route path="instellingen" element={<Settings />} />
            <Route path="profiel" element={<Profile />} />
            <Route
              path="personeel"
              element={
                <ProtectedRoute roles={["restaurant_admin"]}>
                  <Staff />
                </ProtectedRoute>
              }
            />
            <Route
              path="platform"
              element={
                <ProtectedRoute roles={["super_admin"]}>
                  <AdminRestaurants />
                </ProtectedRoute>
              }
            />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
