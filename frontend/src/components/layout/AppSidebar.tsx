import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Receipt,
  CheckSquare,
  Bell,
  Building2,
  FolderTree,
  Tag,
  Users,
  ChevronLeft,
  Menu,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Sheet,
  SheetContent,
  SheetTrigger,
} from '@/components/ui/sheet';
import { useIsMobile } from '@/hooks/use-mobile';

const mainNavItems = [
  { icon: LayoutDashboard, label: 'Dashboard', href: '/dashboard' },
  { icon: Receipt, label: 'Despesas', href: '/expenses' },
  { icon: CheckSquare, label: 'Validações', href: '/validations', requireLeader: true },
  { icon: Bell, label: 'Alertas', href: '/alerts' },
];

const adminNavItems = [
  { icon: Building2, label: 'Empresas', href: '/companies' },
  { icon: FolderTree, label: 'Setores', href: '/departments' },
  { icon: Tag, label: 'Categorias', href: '/categories' },
  { icon: Users, label: 'Usuários', href: '/users' },
];

function SidebarContent({ isCollapsed, onItemClick }: { isCollapsed: boolean; onItemClick?: () => void }) {
  const location = useLocation();
  const { isAdmin, isLeader } = useAuth();

  const isActive = (href: string) => location.pathname === href;

  const NavItem = ({ icon: Icon, label, href }: { icon: React.ElementType; label: string; href: string }) => (
    <Link
      to={href}
      onClick={onItemClick}
      className={cn(
        'group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
        isActive(href)
          ? 'bg-gradient-to-r from-primary/15 to-primary/5 text-primary border-l-[3px] border-primary shadow-sm'
          : 'text-muted-foreground hover:bg-muted/80 hover:text-foreground hover:translate-x-0.5'
      )}
    >
      <Icon className={cn(
        'h-5 w-5 flex-shrink-0 transition-colors duration-200',
        isActive(href) ? 'text-primary' : 'group-hover:text-primary/70'
      )} />
      {!isCollapsed && <span>{label}</span>}
    </Link>
  );

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="p-4 border-b border-border/50">
        <Link to="/dashboard" className="flex items-center gap-2 group">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center shadow-md shadow-primary/20 transition-shadow duration-300 group-hover:shadow-lg group-hover:shadow-primary/30">
            <span className="text-primary-foreground font-bold text-lg">N</span>
          </div>
          {!isCollapsed && (
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold">
                <span className="text-primary">Nitro</span>
                <span className="text-muted-foreground">Subs</span>
              </span>
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4 font-semibold">
                Beta
              </Badge>
            </div>
          )}
        </Link>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto p-4">
        <nav className="space-y-1">
          {mainNavItems.map((item) => {
            if (item.requireLeader && !isLeader) return null;
            return <NavItem key={item.href} {...item} />;
          })}
        </nav>

        {isAdmin && (
          <>
            <div className="mt-6 mb-2">
              {!isCollapsed && (
                <div className="flex items-center gap-2 px-3">
                  <div className="h-px flex-1 bg-gradient-to-r from-primary/30 to-transparent" />
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
                    Cadastros
                  </p>
                  <div className="h-px flex-1 bg-gradient-to-l from-primary/30 to-transparent" />
                </div>
              )}
            </div>
            <nav className="space-y-1">
              {adminNavItems.map((item) => (
                <NavItem key={item.href} {...item} />
              ))}
            </nav>
          </>
        )}
      </div>
    </div>
  );
}

export function AppSidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const isMobile = useIsMobile();

  if (isMobile) {
    return (
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="fixed top-4 left-4 z-50 md:hidden">
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 p-0">
          <SidebarContent isCollapsed={false} />
        </SheetContent>
      </Sheet>
    );
  }

  return (
    <aside
      className={cn(
        'hidden md:flex flex-col bg-card border-r border-border/50 transition-all duration-200',
        isCollapsed ? 'w-[68px]' : 'w-64'
      )}
    >
      <SidebarContent isCollapsed={isCollapsed} />
      
      {/* Collapse toggle */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-20 h-6 w-6 rounded-full border border-border/50 bg-card shadow-sm hover:shadow-md transition-shadow"
      >
        <ChevronLeft className={cn('h-3 w-3 transition-transform', isCollapsed && 'rotate-180')} />
      </Button>
    </aside>
  );
}
