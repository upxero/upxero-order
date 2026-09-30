import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ClipboardList,
  UtensilsCrossed,
  FolderTree,
  Settings,
  Truck,
  Clock,
  Store,
  Menu as MenuIcon,
  X,
  LogOut,
  Shield,
  ExternalLink,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Logo } from "./Logo";

const NAV = [
  { to: "/dashboard", label: "Overzicht", icon: LayoutDashboard, end: true, id: "overzicht" },
  { to: "/dashboard/bestellingen", label: "Bestellingen", icon: ClipboardList, id: "bestellingen" },
  { to: "/dashboard/menu", label: "Menu", icon: UtensilsCrossed, id: "menu" },
  { to: "/dashboard/categorieen", label: "Categorieën", icon: FolderTree, id: "categorieen" },
  { to: "/dashboard/bezorging", label: "Bezorging", icon: Truck, id: "bezorging" },
  { to: "/dashboard/openingstijden", label: "Openingstijden", icon: Clock, id: "openingstijden" },
  { to: "/dashboard/instellingen", label: "Instellingen", icon: Settings, id: "instellingen" },
  { to: "/dashboard/profiel", label: "Profiel", icon: Store, id: "profiel" },
];

export function DashboardLayout() {
  const { user, restaurant, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const navItems = (
    <nav className="flex flex-col gap-1 px-3">
      {NAV.map(({ to, label, icon: Icon, end, id }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={() => setOpen(false)}
          data-testid={`sidebar-nav-${id}`}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
              isActive
                ? "bg-emerald-600 text-white shadow-sm"
                : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
            }`
          }
        >
          <Icon className="h-4.5 w-4.5" size={18} />
          {label}
        </NavLink>
      ))}
      {user?.role === "super_admin" && (
        <NavLink
          to="/dashboard/platform"
          onClick={() => setOpen(false)}
          data-testid="sidebar-nav-platform"
          className={({ isActive }) =>
            `mt-1 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
              isActive ? "bg-emerald-600 text-white" : "text-slate-400 hover:bg-slate-800 hover:text-slate-100"
            }`
          }
        >
          <Shield className="h-4.5 w-4.5" size={18} />
          Platform
        </NavLink>
      )}
    </nav>
  );

  const sidebarInner = (
    <div className="flex h-full flex-col bg-slate-900">
      <div className="flex items-center justify-between px-5 py-5">
        <div className="rounded-lg bg-white/5 px-1 py-0.5">
          <Logo />
        </div>
        <button className="lg:hidden text-slate-400" onClick={() => setOpen(false)} data-testid="sidebar-close">
          <X className="h-5 w-5" />
        </button>
      </div>
      <div className="mx-4 mb-4 rounded-lg border border-slate-800 bg-slate-800/50 px-3 py-2.5">
        <p className="truncate text-sm font-semibold text-slate-100">{restaurant?.name || "Upxero"}</p>
        <p className="truncate text-xs text-slate-400">{user?.name} · {user?.role === "restaurant_admin" ? "Beheerder" : user?.role === "restaurant_staff" ? "Medewerker" : "Platform"}</p>
      </div>
      <div className="flex-1 overflow-y-auto scroll-thin">{navItems}</div>
      {restaurant?.slug && (
        <a
          href={`/order/${restaurant.slug}`}
          target="_blank"
          rel="noreferrer"
          data-testid="sidebar-view-order-page"
          className="mx-3 mb-2 flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2.5 text-xs font-medium text-slate-300 hover:bg-slate-800"
        >
          <ExternalLink className="h-4 w-4" /> Bekijk bestelpagina
        </a>
      )}
      <button
        onClick={handleLogout}
        data-testid="sidebar-logout"
        className="mx-3 mb-4 flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-100"
      >
        <LogOut className="h-4.5 w-4.5" size={18} /> Uitloggen
      </button>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 lg:block">{sidebarInner}</aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72">{sidebarInner}</div>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur lg:hidden">
          <button onClick={() => setOpen(true)} data-testid="sidebar-open" className="text-slate-700">
            <MenuIcon className="h-6 w-6" />
          </button>
          <Logo compact />
          <span className="font-heading text-sm font-semibold text-slate-900">{restaurant?.name || "Upxero"}</span>
        </header>
        <main className="p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
