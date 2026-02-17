import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  DollarSign,
  CheckCircle2,
  Bell,
  TrendingUp,
  Calendar,
  Repeat,
  XCircle,
  AlertTriangle,
  Loader2,
  Filter,
  PieChart as PieChartIcon,
  BarChart3,
  LineChart as LineChartIcon,
} from 'lucide-react';
import { dashboardApi, companiesApi } from '@/services/api';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { formatCurrency, formatDate, formatMonth, getStatusBadgeVariant, getStatusLabel, getAlertTypeIcon } from '@/lib/formatters';
import { Link } from 'react-router-dom';
import type { DashboardFilters, Currency } from '@/types';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { ExpenseLineChart } from '@/components/dashboard/ExpenseLineChart';
import { ExpensePieChart } from '@/components/dashboard/ExpensePieChart';
import { ExpenseBarChart } from '@/components/dashboard/ExpenseBarChart';
import { TopExpensesChart } from '@/components/dashboard/TopExpensesChart';

function MetricCard({
  title,
  value,
  icon: Icon,
  description,
  loading,
}: {
  title: string;
  value: string | number;
  icon: React.ElementType;
  description?: string;
  loading?: boolean;
}) {
  return (
    <Card className="group glow-primary gradient-border transition-all duration-200 hover:-translate-y-0.5">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            {loading ? (
              <Skeleton className="h-8 w-32 mt-2" />
            ) : (
              <p className="text-2xl font-bold mt-2 tabular-nums">{value}</p>
            )}
            {description && (
              <p className="text-xs text-muted-foreground mt-1">{description}</p>
            )}
          </div>
          <div className="p-3 bg-gradient-to-br from-primary/20 to-primary/5 rounded-xl transition-all duration-300 group-hover:from-primary/30 group-hover:to-primary/10 group-hover:shadow-md group-hover:shadow-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function getMonthOptions() {
  const options: { value: string; label: string }[] = [];
  const now = new Date();
  for (let i = 0; i < 6; i++) {
    const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    options.push({ value, label: formatMonth(value) });
  }
  return options;
}

// Taxa de câmbio padrão USD/BRL (pode ser substituída por busca do backend)
const DEFAULT_EXCHANGE_RATE = 5.50;

export default function DashboardPage() {
  const { user } = useAuth();
  const [filters, setFilters] = useState<DashboardFilters>({});
  const [currency, setCurrency] = useState<Currency>('BRL');
  const selectedCompanyId = filters.company_id;

  // Função helper para converter valores BRL para USD
  const convertToCurrency = (valueBRL: number): number => {
    if (currency === 'USD') {
      return valueBRL / DEFAULT_EXCHANGE_RATE;
    }
    return valueBRL;
  };

  const { data: companies } = useQuery({
    queryKey: ['companies'],
    queryFn: companiesApi.getAll,
  });

  const monthOptions = getMonthOptions();

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats', filters],
    queryFn: () => dashboardApi.getStats(filters),
  });

  const { data: expensesByCategory, isLoading: categoryLoading } = useQuery({
    queryKey: ['expenses-by-category', filters],
    queryFn: () => dashboardApi.getExpensesByCategory(filters, 10),
  });

  const { data: expensesByCompany, isLoading: companyLoading } = useQuery({
    queryKey: ['expenses-by-company', filters],
    queryFn: () => dashboardApi.getExpensesByCompany(filters, 10),
  });

  const { data: expensesByDepartment, isLoading: departmentLoading } = useQuery({
    queryKey: ['expenses-by-department', filters],
    queryFn: () => dashboardApi.getExpensesByDepartment(filters, 10),
  });

  const { data: timelineData, isLoading: timelineLoading } = useQuery({
    queryKey: ['expenses-timeline', filters],
    queryFn: () => dashboardApi.getExpensesTimeline(filters, 6),
  });

  const { data: topExpenses, isLoading: topExpensesLoading } = useQuery({
    queryKey: ['top-expenses', filters],
    queryFn: () => dashboardApi.getTopExpenses(filters, 10),
  });

  const { data: recentExpenses, isLoading: expensesLoading } = useQuery({
    queryKey: ['recent-expenses', filters],
    queryFn: () => dashboardApi.getRecentExpenses(5, filters),
  });

  const { data: recentAlerts, isLoading: alertsLoading } = useQuery({
    queryKey: ['recent-alerts'],
    queryFn: () => dashboardApi.getRecentAlerts(5),
  });

  const hasActiveFilters = !!(
    filters.company_id ||
    filters.month
  );

  const clearFilters = () => setFilters({});

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Visão geral das despesas e atividades
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium text-muted-foreground">Filtros:</span>
            <Select
              value={filters.company_id ?? 'all'}
              onValueChange={(v) =>
                setFilters((prev) => ({
                  ...prev,
                  company_id: v === 'all' ? undefined : v,
                }))
              }
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Empresa" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas as empresas</SelectItem>
                {(user?.role === 'leader' && user.companies
                  ? companies?.filter((c) => user.companies?.some((uc) => uc.id === c.id))
                  : companies
                )?.map((company) => (
                  <SelectItem key={company.id} value={company.id}>
                    {company.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={filters.month ?? 'all'}
              onValueChange={(v) =>
                setFilters((prev) => ({
                  ...prev,
                  month: v === 'all' ? undefined : v,
                }))
              }
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Mês (validações)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos os meses</SelectItem>
                {monthOptions.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {hasActiveFilters && (
              <Button variant="ghost" size="sm" onClick={clearFilters} className="text-muted-foreground">
                Limpar filtros
              </Button>
            )}
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">Moeda:</span>
              <ToggleGroup type="single" value={currency} onValueChange={(value) => value && setCurrency(value as Currency)}>
                <ToggleGroupItem value="BRL" aria-label="Real Brasileiro">
                  BRL
                </ToggleGroupItem>
                <ToggleGroupItem value="USD" aria-label="Dólar Americano">
                  USD
                </ToggleGroupItem>
              </ToggleGroup>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Metric Cards - Grid 2x4 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Total de Despesas"
          value={formatCurrency(convertToCurrency(stats?.total_expenses_value || 0), currency)}
          icon={DollarSign}
          loading={statsLoading}
          description="Todas as despesas ativas"
        />
        <MetricCard
          title="Total Mensal"
          value={formatCurrency(convertToCurrency(stats?.monthly_expenses_value || 0), currency)}
          icon={Calendar}
          loading={statsLoading}
          description="Despesas do mês atual"
        />
        <MetricCard
          title="Média por Despesa"
          value={formatCurrency(convertToCurrency(stats?.average_expense_value || 0), currency)}
          icon={TrendingUp}
          loading={statsLoading}
          description="Valor médio"
        />
        <MetricCard
          title="Despesas Recorrentes"
          value={stats?.recurring_expenses || 0}
          icon={Repeat}
          loading={statsLoading}
          description={`vs ${stats?.one_time_expenses || 0} únicas`}
        />
        <MetricCard
          title="Validações Pendentes"
          value={stats?.pending_validations || 0}
          icon={CheckCircle2}
          loading={statsLoading}
          description="Aguardando validação"
        />
        <MetricCard
          title="Alertas Não Lidos"
          value={stats?.unread_alerts || 0}
          icon={Bell}
          loading={statsLoading}
          description="Novos alertas"
        />
        <MetricCard
          title="Despesas Ativas"
          value={stats?.active_expenses || 0}
          icon={TrendingUp}
          loading={statsLoading}
          description="Total de despesas ativas"
        />
        <MetricCard
          title="Próximas Renovações"
          value={stats?.upcoming_renewals || 0}
          icon={AlertTriangle}
          loading={statsLoading}
          description="Nos próximos 30 dias"
        />
      </div>

      {/* Gráfico de Linha - Evolução */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LineChartIcon className="h-5 w-5" />
            Evolução de Gastos (Últimos 6 Meses)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {timelineLoading ? (
            <div className="h-[300px] flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : timelineData?.data && timelineData.data.length > 0 ? (
            <ExpenseLineChart data={timelineData.data} currency={currency} exchangeRate={DEFAULT_EXCHANGE_RATE} />
          ) : (
            <p className="text-muted-foreground text-center py-8">
              Nenhum dado disponível para o período selecionado
            </p>
          )}
        </CardContent>
      </Card>

      {/* Gráficos - Pizza e Top Despesas */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChartIcon className="h-5 w-5" />
              Distribuição por Categoria
            </CardTitle>
          </CardHeader>
          <CardContent>
            {categoryLoading ? (
              <div className="h-[300px] flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : expensesByCategory?.items && expensesByCategory.items.length > 0 ? (
              <ExpensePieChart data={expensesByCategory.items} currency={currency} exchangeRate={DEFAULT_EXCHANGE_RATE} />
            ) : (
              <p className="text-muted-foreground text-center py-8">
                Nenhuma categoria encontrada
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Top 10 Maiores Despesas
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topExpensesLoading ? (
              <div className="h-[300px] flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : topExpenses?.items && topExpenses.items.length > 0 ? (
              <TopExpensesChart data={topExpenses.items} currency={currency} exchangeRate={DEFAULT_EXCHANGE_RATE} />
            ) : (
              <p className="text-muted-foreground text-center py-8">
                Nenhuma despesa encontrada
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Gráficos - Empresas e Setores */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Gastos por Empresa
            </CardTitle>
          </CardHeader>
          <CardContent>
            {companyLoading ? (
              <div className="h-[300px] flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : expensesByCompany?.items && expensesByCompany.items.length > 0 ? (
              <ExpenseBarChart
                data={expensesByCompany.items.map((item) => ({
                  name: item.company_name,
                  value: item.total_value,
                  count: item.count,
                }))}
                title=""
                currency={currency}
                exchangeRate={DEFAULT_EXCHANGE_RATE}
              />
            ) : (
              <p className="text-muted-foreground text-center py-8">
                Nenhuma empresa encontrada
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Gastos por Setor
            </CardTitle>
          </CardHeader>
          <CardContent>
            {departmentLoading ? (
              <div className="h-[300px] flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : expensesByDepartment?.items && expensesByDepartment.items.length > 0 ? (
              <ExpenseBarChart
                data={expensesByDepartment.items.map((item) => ({
                  name: `${item.department_name} (${item.company_name})`,
                  value: item.total_value,
                  count: item.count,
                }))}
                title=""
                currency={currency}
                exchangeRate={DEFAULT_EXCHANGE_RATE}
              />
            ) : (
              <p className="text-muted-foreground text-center py-8">
                Nenhum setor encontrado
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Data */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recent Expenses */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Despesas Recentes</CardTitle>
            <Link to="/expenses" className="text-sm text-primary hover:underline">
              Ver todas
            </Link>
          </CardHeader>
          <CardContent>
            {expensesLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : recentExpenses?.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">
                Nenhuma despesa encontrada
              </p>
            ) : (
              <div className="space-y-3">
                {recentExpenses?.map((expense) => (
                  <div
                    key={expense.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-muted/50 hover:bg-muted transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="font-medium truncate">{expense.service_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {expense.company?.name} • {expense.department?.name}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 flex-shrink-0">
                      <span className="font-medium tabular-nums">
                        {formatCurrency(convertToCurrency(expense.value_brl || 0), currency)}
                      </span>
                      <Badge variant={getStatusBadgeVariant(expense.status)}>
                        {getStatusLabel(expense.status)}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Alerts */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Alertas Recentes</CardTitle>
            <Link to="/alerts" className="text-sm text-primary hover:underline">
              Ver todos
            </Link>
          </CardHeader>
          <CardContent>
            {alertsLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : recentAlerts?.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">
                Nenhum alerta encontrado
              </p>
            ) : (
              <div className="space-y-3">
                {recentAlerts?.map((alert) => {
                  const AlertIcon = getAlertTypeIcon(alert.alert_type);
                  return (
                    <div
                      key={alert.id}
                      className={`flex items-start gap-3 p-3 rounded-lg transition-colors ${
                        alert.status === 'pending' ? 'bg-warning-light' : 'bg-muted/50'
                      }`}
                    >
                      <div className={`p-2 rounded-lg ${
                        alert.status === 'pending' ? 'bg-warning/10' : 'bg-muted'
                      }`}>
                        <AlertIcon className={`h-4 w-4 ${
                          alert.status === 'pending' ? 'text-warning' : 'text-muted-foreground'
                        }`} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-sm">{alert.title}</p>
                        <p className="text-xs text-muted-foreground truncate">
                          {alert.message}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatDate(alert.created_at)}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
