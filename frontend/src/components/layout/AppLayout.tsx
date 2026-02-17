import { Outlet } from 'react-router-dom';
import { AppSidebar } from './AppSidebar';
import { AppHeader } from './AppHeader';
import { Footer } from './Footer';

export function AppLayout() {
  return (
    <div className="min-h-screen flex flex-col w-full bg-background">
      <div className="flex flex-1">
        <AppSidebar />
        <main className="flex-1 overflow-auto flex flex-col">
          <AppHeader />
          <div className="flex-1 p-4 md:p-8 max-w-[1400px] mx-auto">
            <Outlet />
          </div>
          <Footer />
        </main>
      </div>
    </div>
  );
}
