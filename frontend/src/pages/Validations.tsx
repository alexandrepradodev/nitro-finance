import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, XCircle, Loader2, Calendar, PartyPopper, Clock, User, Filter, Download } from 'lucide-react';
import { validationsApi, companiesApi, usersApi, departmentsApi } from '@/services/api';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useToast } from '@/hooks/use-toast';
import { formatCurrency, formatMonth, formatDate } from '@/lib/formatters';
import type { ValidationStatus, ExpenseValidation } from '@/types';

function getMonthOptions() {
  const options = [];
  const now = new Date();
  
  // Meses passados (12 meses)
  for (let i = 0; i < 12; i++) {
    const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    options.push({ value, label: formatMonth(value) });
  }
  
  // Meses futuros (24 meses = 2 anos)
  for (let i = 1; i <= 24; i++) {
    const date = new Date(now.getFullYear(), now.getMonth() + i, 1);
    const value = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    options.push({ value, label: formatMonth(value) + ' (previsto)' });
  }
  
  return options;
}

function escapeCsvCell(value: string): string {
  const s = String(value ?? '');
  if (s.includes(';') || s.includes('"')) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

function buildValidationsCsv(
  validations: ExpenseValidation[],
  formatCurrencyFn: (v: number, currency?: string) => string,
  formatMonthFn: (s: string) => string
): string {
  const header = 'Código;Serviço;Empresa;Setor;Responsável;Valor;Status;Mês;Data de renovação;Validado por;Data';
  const statusLabels: Record<string, string> = {
    pending: 'Pendente',
    approved: 'Aprovada',
    rejected: 'Rejeitada',
  };
  const rows = validations.map((v) => {
    const expense = v.expense;
    const code = expense?.code ?? '';
    const service = expense?.service_name ?? '';
    const company = expense?.company?.name ?? '';
    const department = expense?.department?.name ?? '';
    const owner = expense?.owner?.name ?? '';
    const value =
      expense != null
        ? formatCurrencyFn(Number(expense.value ?? 0), expense.currency ?? 'BRL')
        : '';
    const status = statusLabels[v.status] ?? v.status;
    const month = v.validation_month ? formatMonthFn(v.validation_month) : '';
    const renewalDate = expense?.renewal_date ? formatDate(expense.renewal_date) : '';
    const validator = v.validator?.name ?? '';
    const date = v.validated_at ? formatDate(v.validated_at) : '';
    return [code, service, company, department, owner, value, status, month, renewalDate, validator, date]
      .map(escapeCsvCell)
      .join(';');
  });
  return [header, ...rows].join('\r\n');
}

function downloadCsv(csvContent: string, filename: string): void {
  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ValidationsPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedMonth, setSelectedMonth] = useState<string>(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  });
  const [activeTab, setActiveTab] = useState<ValidationStatus | 'all'>('pending');
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectChargedChoice, setRejectChargedChoice] = useState<boolean | null>(null);
  const [filters, setFilters] = useState<{
    company_id?: string;
    owner_id?: string;
    department_id?: string;
    service_name?: string;
  }>({});

  const monthOptions = getMonthOptions();

  // Queries para empresas e departamentos
  const { data: companies } = useQuery({
    queryKey: ['companies'],
    queryFn: companiesApi.getAll,
  });

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.getAll,
  });

  const { data: departments } = useQuery({
    queryKey: ['departments'],
    queryFn: () => departmentsApi.getAll(),
  });

  const filteredDepartments = useMemo(() => {
    if (!filters.company_id) return [];
    return (departments ?? []).filter(
      (department) => department.is_active && department.company_id === filters.company_id
    );
  }, [departments, filters.company_id]);

  // Detectar se é mês futuro
  const isFutureMonth = (() => {
    const now = new Date();
    const [year, month] = selectedMonth.split('-').map(Number);
    const selected = new Date(year, month - 1, 1);
    const currentMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);
    return selected > currentMonthStart;
  })();

  // Query para validações previstas (meses futuros)
  const { data: predictedValidations, isLoading: isLoadingPredicted } = useQuery({
    queryKey: ['validations-predicted', selectedMonth],
    queryFn: () => validationsApi.getPredicted(selectedMonth),
    enabled: isFutureMonth, // Só busca se for mês futuro
  });

  // Query para histórico completo (meses passados/atuais)
  const { data: historyValidations, isLoading: isLoadingHistory } = useQuery({
    queryKey: ['validations-history', selectedMonth, activeTab],
    queryFn: () => {
      const filters: { month?: string; status?: string } = {
        month: `${selectedMonth}-01`,
      };
      if (activeTab !== 'all') {
        filters.status = activeTab;
      }
      return validationsApi.getHistory(filters);
    },
    enabled: !isFutureMonth, // Só busca se não for mês futuro
  });

  // Query para pendentes (mantida para compatibilidade - meses passados/atuais)
  const { data: pendingValidations, isLoading: isLoadingPending } = useQuery({
    queryKey: ['validations-pending', selectedMonth],
    queryFn: () => validationsApi.getPending(`${selectedMonth}-01`),
    enabled: !isFutureMonth, // Só busca se não for mês futuro
  });

  const isLoading = isLoadingHistory || isLoadingPending || isLoadingPredicted;

  // Determinar quais validações mostrar baseado na tab ativa e se é mês futuro
  const validations = isFutureMonth
    ? predictedValidations || []
    : activeTab === 'pending'
    ? pendingValidations || []
    : historyValidations || [];

  // Aplicar filtros de empresa, responsável e nome
  const filteredValidations = useMemo(() => {
    return validations.filter((validation) => {
      if (filters.company_id && validation.expense?.company?.id !== filters.company_id) {
        return false;
      }
      if (filters.owner_id && validation.expense?.owner?.id !== filters.owner_id) {
        return false;
      }
      if (filters.department_id && validation.expense?.department?.id !== filters.department_id) {
        return false;
      }
      if (filters.service_name) {
        const term = filters.service_name.toLowerCase();
        if (!validation.expense?.service_name?.toLowerCase().includes(term)) return false;
      }
      return true;
    });
  }, [validations, filters.company_id, filters.owner_id, filters.department_id, filters.service_name]);

  // Calcular totais
  const totals = useMemo(() => {
    if (!filteredValidations || filteredValidations.length === 0) return 0;
    
    return filteredValidations.reduce((acc, validation) => {
      const expense = validation.expense;
      if (!expense) return acc;
      
      // Usar value_brl se disponível e válido (já está convertido para BRL)
      if (expense.value_brl != null && !isNaN(Number(expense.value_brl))) {
        return acc + Number(expense.value_brl);
      }
      
      // Caso contrário, usar value convertido conforme a moeda
      if (expense.value != null && !isNaN(Number(expense.value))) {
        const value = Number(expense.value);
        
        if (expense.currency === 'BRL') {
          return acc + value;
        } else if (expense.currency === 'USD') {
          // Converter USD para BRL usando exchange_rate
          const rate = expense.exchange_rate != null && !isNaN(Number(expense.exchange_rate)) && Number(expense.exchange_rate) > 0
            ? Number(expense.exchange_rate)
            : 1;
          return acc + (value * rate);
        }
      }
      
      return acc;
    }, 0);
  }, [filteredValidations]);

  const approveMutation = useMutation({
    mutationFn: validationsApi.approve,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validations'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['validations-history'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['validations-pending'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['validations-predicted'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['expenses'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['dashboard'], exact: false });
      toast({
        title: 'Despesa aprovada!',
        description: 'A validação foi registrada com sucesso.',
      });
    },
    onError: () => {
      toast({
        variant: 'destructive',
        title: 'Erro ao aprovar',
        description: 'Não foi possível aprovar a despesa.',
      });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, charged_this_month }: { id: string; charged_this_month: boolean }) =>
      validationsApi.reject(id, { charged_this_month }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validations'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['validations-history'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['validations-pending'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['validations-predicted'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['expenses'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'], exact: false });
      queryClient.invalidateQueries({ queryKey: ['dashboard'], exact: false });
      setRejectingId(null);
      setRejectChargedChoice(null);
      toast({
        title: 'Despesa cancelada',
        description: 'A validação foi registrada e a despesa foi cancelada.',
      });
    },
    onError: () => {
      toast({
        variant: 'destructive',
        title: 'Erro ao rejeitar',
        description: 'Não foi possível rejeitar a despesa.',
      });
    },
  });

  const handleApprove = (id: string) => {
    approveMutation.mutate(id);
  };

  const handleReject = () => {
    if (rejectingId != null && rejectChargedChoice !== null) {
      rejectMutation.mutate({ id: rejectingId, charged_this_month: rejectChargedChoice });
    }
  };

  const openRejectQuestion = (id: string) => {
    setRejectingId(id);
    setRejectChargedChoice(null);
  };

  const closeRejectFlow = () => {
    setRejectingId(null);
    setRejectChargedChoice(null);
  };

  const handleCompanyChange = (value: string) => {
    const companyId = value === 'all' ? undefined : value;
    setFilters({ ...filters, company_id: companyId, department_id: undefined });
  };

  const handleOwnerChange = (value: string) => {
    const ownerId = value === 'all' ? undefined : value;
    setFilters({ ...filters, owner_id: ownerId });
  };

  const handleDepartmentChange = (value: string) => {
    const departmentId = value === 'all' ? undefined : value;
    setFilters({ ...filters, department_id: departmentId });
  };

  const clearFilters = () => {
    setFilters({});
  };

  const handleExportCsv = () => {
    if (!filteredValidations?.length) return;
    const csv = buildValidationsCsv(filteredValidations, formatCurrency, formatMonth);
    const filename = `validacoes-${selectedMonth}-${activeTab}.csv`;
    downloadCsv(csv, filename);
    toast({
      title: 'Exportação concluída',
      description: `${filteredValidations.length} validação(ões) exportada(s).`,
    });
  };

  const getStatusBadge = (status: ValidationStatus, isOverdue: boolean, isPredicted?: boolean) => {
    if (isPredicted) {
      return (
        <Badge variant="outline" className="border-blue-500 text-blue-600">
          <Calendar className="h-3 w-3 mr-1" />
          Prevista
        </Badge>
      );
    }
    if (isOverdue && status === 'pending') {
      return (
        <Badge variant="destructive" className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          Atrasado
        </Badge>
      );
    }
    switch (status) {
      case 'approved':
        return (
          <Badge variant="default" className="bg-success text-success-foreground">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Aprovada
          </Badge>
        );
      case 'rejected':
        return (
          <Badge variant="destructive">
            <XCircle className="h-3 w-3 mr-1" />
            Rejeitada
          </Badge>
        );
      default:
        return (
          <Badge variant="outline">
            <Clock className="h-3 w-3 mr-1" />
            Pendente
          </Badge>
        );
    }
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Validações</h1>
          <p className="text-muted-foreground mt-1">
            Visualize e valide despesas recorrentes
          </p>
        </div>

        <Select value={selectedMonth ?? ''} onValueChange={setSelectedMonth}>
          <SelectTrigger className="w-[200px]">
            <Calendar className="h-4 w-4 mr-2" />
            <SelectValue placeholder="Mês" />
          </SelectTrigger>
          <SelectContent>
            {monthOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          onClick={handleExportCsv}
          disabled={isLoading || !filteredValidations?.length}
        >
          <Download className="h-4 w-4 mr-2" />
          Exportar CSV
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-end gap-3">
            <Filter className="h-4 w-4 text-muted-foreground mb-2" />
            <span className="text-sm font-medium text-muted-foreground mb-2">Filtros:</span>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Nome</Label>
              <Input
                placeholder="Buscar por nome..."
                value={filters.service_name ?? ''}
                onChange={(e) =>
                  setFilters({ ...filters, service_name: e.target.value || undefined })
                }
                className="h-9 w-[220px]"
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Empresa</Label>
              <Select
                value={filters.company_id ?? 'all'}
                onValueChange={handleCompanyChange}
              >
                <SelectTrigger className="h-9 w-[200px]">
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
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Responsável</Label>
              <Select
                value={filters.owner_id ?? 'all'}
                onValueChange={handleOwnerChange}
              >
                <SelectTrigger className="h-9 w-[200px]">
                  <SelectValue placeholder="Responsável" />
                </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos os responsáveis</SelectItem>
                {(user?.role === 'leader' && user
                  ? [user]
                  : users?.filter((u) => u.is_active)
                    ?.filter((u, index, self) => 
                      index === self.findIndex((us) => us.id === u.id)
                    )
                )?.map((u) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.name || u.email}
                  </SelectItem>
                ))}
              </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs text-muted-foreground">Setor</Label>
              <Select
                value={filters.department_id ?? 'all'}
                onValueChange={handleDepartmentChange}
                disabled={!filters.company_id}
              >
                {!filters.company_id ? (
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="inline-block">
                          <SelectTrigger className="h-9 w-[200px]" disabled>
                            <SelectValue placeholder="Selecione uma empresa primeiro" />
                          </SelectTrigger>
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>
                        Selecione uma empresa primeiro
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                ) : (
                  <SelectTrigger className="h-9 w-[200px]">
                    <SelectValue placeholder="Setor" />
                  </SelectTrigger>
                )}
                <SelectContent>
                  {filters.company_id ? (
                    <>
                      <SelectItem value="all">Todos os setores</SelectItem>
                      {filteredDepartments.map((department) => (
                        <SelectItem key={department.id} value={department.id}>
                          {department.name}
                        </SelectItem>
                      ))}
                    </>
                  ) : null}
                </SelectContent>
              </Select>
            </div>
            {(filters.company_id || filters.owner_id || filters.department_id || filters.service_name) && (
              <Button variant="ghost" onClick={clearFilters} className="text-muted-foreground">
                Limpar filtros
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as ValidationStatus | 'all')}>
        <TabsList>
          <TabsTrigger value="pending">Pendentes</TabsTrigger>
          <TabsTrigger value="approved">Aprovadas</TabsTrigger>
          <TabsTrigger value="rejected">Rejeitadas</TabsTrigger>
          <TabsTrigger value="all">Todas</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-6">
          {/* Content */}
          {isLoading ? (
            <Card>
              <CardContent className="p-0">
                <Table className="text-xs">
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead className="font-semibold">Código</TableHead>
                      <TableHead className="font-semibold">Serviço</TableHead>
                      <TableHead className="font-semibold">Empresa</TableHead>
                      <TableHead className="font-semibold">Setor</TableHead>
                      <TableHead className="font-semibold">Responsável</TableHead>
                      <TableHead className="font-semibold text-right">Valor</TableHead>
                      <TableHead className="font-semibold">Status</TableHead>
                      <TableHead className="font-semibold">Mês</TableHead>
                      <TableHead className="font-semibold">Validado por</TableHead>
                      <TableHead className="font-semibold">Data</TableHead>
                      <TableHead className="font-semibold w-[150px]">Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {[...Array(5)].map((_, i) => (
                      <TableRow key={i}>
                        <TableCell><Skeleton className="h-4 w-12" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                        <TableCell className="text-right"><Skeleton className="h-4 w-20 ml-auto" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-16" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                        <TableCell><Skeleton className="h-4 w-20" /></TableCell>
                        <TableCell><Skeleton className="h-8 w-32" /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ) : filteredValidations?.length === 0 ? (
            <Card className="py-12">
              <CardContent className="text-center">
                <div className="mx-auto w-16 h-16 rounded-full bg-success-light flex items-center justify-center mb-4">
                  <PartyPopper className="h-8 w-8 text-success" />
                </div>
                <h3 className="font-medium text-xl">
                  {isFutureMonth
                    ? 'Nenhuma validação prevista'
                    : activeTab === 'pending'
                    ? 'Nenhuma validação pendente 🎉'
                    : activeTab === 'approved'
                    ? 'Nenhuma validação aprovada'
                    : activeTab === 'rejected'
                    ? 'Nenhuma validação rejeitada'
                    : 'Nenhuma validação encontrada'}
                </h3>
                <p className="text-muted-foreground mt-2">
                  {filters.company_id || filters.department_id
                    ? 'Nenhuma validação encontrada com os filtros aplicados. Tente ajustar os filtros.'
                    : isFutureMonth
                    ? `Não há despesas recorrentes ativas que gerarão validações em ${formatMonth(selectedMonth)}.`
                    : activeTab === 'pending'
                    ? `Todas as despesas de ${formatMonth(selectedMonth)} foram validadas.`
                    : `Não há validações ${activeTab === 'all' ? '' : activeTab === 'approved' ? 'aprovadas' : 'rejeitadas'} para ${formatMonth(selectedMonth)}.`}
                </p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <Table className="text-xs">
                    <TableHeader>
                      <TableRow className="bg-muted/50">
                        <TableHead className="font-semibold">Código</TableHead>
                        <TableHead className="font-semibold">Serviço</TableHead>
                        <TableHead className="font-semibold">Empresa</TableHead>
                        <TableHead className="font-semibold">Setor</TableHead>
                        <TableHead className="font-semibold">Responsável</TableHead>
                        <TableHead className="font-semibold text-right">Valor</TableHead>
                        <TableHead className="font-semibold">Status</TableHead>
                        <TableHead className="font-semibold">Mês</TableHead>
                        <TableHead className="font-semibold">Data de renovação</TableHead>
                        <TableHead className="font-semibold">Validado por</TableHead>
                        <TableHead className="font-semibold">Data</TableHead>
                        <TableHead className="font-semibold w-[150px]">Ações</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredValidations?.map((validation, index) => (
                        <TableRow
                          key={validation.id || `predicted-${validation.expense_id}-${validation.validation_month}-${index}`}
                          className={`hover:bg-muted/50 transition-colors ${
                            validation.is_overdue && validation.status === 'pending'
                              ? 'border-l-4 border-destructive'
                              : ''
                          } ${validation.status === 'rejected' ? 'opacity-60' : ''}`}
                        >
                          <TableCell>
                            <span className="font-mono tabular-nums">{validation.expense?.code ?? '—'}</span>
                          </TableCell>
                          <TableCell>
                            <div className="space-y-1">
                              <p className="font-medium">{validation.expense?.service_name || 'N/A'}</p>
                              {validation.expense?.category?.name && (
                                <p className="text-muted-foreground">{validation.expense.category.name}</p>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <span className="truncate block max-w-[150px]">
                              {validation.expense?.company?.name || '—'}
                            </span>
                          </TableCell>
                          <TableCell>
                            <span className="truncate block max-w-[150px]">
                              {validation.expense?.department?.name || '—'}
                            </span>
                          </TableCell>
                          <TableCell>
                            {validation.expense?.owner ? (
                              <div className="flex items-center gap-1">
                                <User className="h-3 w-3 text-muted-foreground" />
                                <span className="truncate max-w-[120px]">{validation.expense.owner.name}</span>
                              </div>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <span className="font-semibold tabular-nums">
                              {formatCurrency(
                                validation.expense?.value || 0,
                                validation.expense?.currency
                              )}
                            </span>
                          </TableCell>
                          <TableCell>
                            {getStatusBadge(validation.status, validation.is_overdue, validation.is_predicted)}
                          </TableCell>
                          <TableCell>
                            <span>{formatMonth(validation.validation_month)}</span>
                          </TableCell>
                          <TableCell>
                            {validation.expense?.renewal_date ? (
                              <span>
                                {new Date(validation.expense.renewal_date).toLocaleDateString('pt-BR')}
                              </span>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {validation.validator ? (
                              <div className="flex items-center gap-1">
                                <User className="h-3 w-3 text-muted-foreground" />
                                <span className="truncate max-w-[120px]">{validation.validator.name}</span>
                              </div>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {validation.validated_at ? (
                              <div className="flex items-center gap-1">
                                <Calendar className="h-3 w-3 text-muted-foreground" />
                                <span>
                                  {new Date(validation.validated_at).toLocaleDateString('pt-BR')}
                                </span>
                              </div>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {validation.status === 'pending' && !validation.is_predicted && validation.id ? (
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  onClick={() => handleApprove(validation.id!)}
                                  disabled={approveMutation.isPending}
                                  className="bg-success hover:bg-success/90 text-success-foreground"
                                >
                                  {approveMutation.isPending &&
                                  approveMutation.variables === validation.id ? (
                                    <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                                  ) : (
                                    <CheckCircle2 className="h-3 w-3 mr-1" />
                                  )}
                                  Aprovar
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => openRejectQuestion(validation.id!)}
                                  disabled={rejectMutation.isPending}
                                  className="border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground"
                                >
                                  <XCircle className="h-3 w-3 mr-1" />
                                  Cancelar
                                </Button>
                              </div>
                            ) : (
                              <span className="text-muted-foreground">—</span>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                    <TableFooter>
                      <TableRow className="bg-muted/50">
                        <TableCell colSpan={5} className="font-semibold">
                          Total
                        </TableCell>
                        <TableCell className="text-right font-semibold tabular-nums">
                          {formatCurrency(isNaN(totals) ? 0 : totals, 'BRL')}
                        </TableCell>
                        <TableCell colSpan={5}></TableCell>
                      </TableRow>
                    </TableFooter>
                  </Table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Pergunta: despesa já foi processada? */}
      <Dialog open={!!rejectingId && rejectChargedChoice === null} onOpenChange={(open) => !open && closeRejectFlow()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Cancelar despesa</DialogTitle>
            <DialogDescription>
              Essa despesa já foi processada? O valor deste mês será contabilizado no dashboard apenas se você responder Sim.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setRejectChargedChoice(false)}>
              Não
            </Button>
            <Button onClick={() => setRejectChargedChoice(true)}>
              Sim
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirmação de cancelamento */}
      <AlertDialog open={!!rejectingId && rejectChargedChoice !== null} onOpenChange={(open) => !open && closeRejectFlow()}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmar cancelamento</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja cancelar esta despesa? A despesa será cancelada
              e esta ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Voltar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleReject}
              className="bg-destructive hover:bg-destructive/90"
            >
              {rejectMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : null}
              Confirmar cancelamento
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
