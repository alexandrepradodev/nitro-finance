import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { AppSidebar } from './AppSidebar';
import { AppHeader } from './AppHeader';
import { Footer } from './Footer';

export function AppLayout() {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const handleToggleSidebar = () => setIsSidebarCollapsed((prev) => !prev);

  return (
    <div className="min-h-screen flex flex-col w-full bg-background">
      <div className="flex flex-1">
        <AppSidebar isCollapsed={isSidebarCollapsed} />
        <main className="flex-1 overflow-auto flex flex-col">
          <AppHeader isSidebarCollapsed={isSidebarCollapsed} onToggleSidebar={handleToggleSidebar} />
          <div className="flex-1 p-4 md:p-8 max-w-[1400px] mx-auto">
            <Outlet />
          </div>
          <Footer />
        </main>
      </div>
    </div>
  );
}
