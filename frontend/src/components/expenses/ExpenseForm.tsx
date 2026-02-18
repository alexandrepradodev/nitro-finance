import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Loader2, CalendarIcon } from 'lucide-react';
import { AxiosError } from 'axios';
import { expensesApi, companiesApi, departmentsApi, categoriesApi, usersApi } from '@/services/api';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ptBR } from 'date-fns/locale';
import type { Expense, ExpenseFormData, ExpenseUpdatePayload, ExpenseType, Currency, Periodicity, PaymentMethod } from '@/types';

// Formata número para padrão brasileiro: 1.234,56
function formatNumberToBr(num: number): string {
  if (Number.isNaN(num) || num === 0) return '';
  const fixed = num.toFixed(2);
  const [intPart, decPart] = fixed.split('.');
  const withDots = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${withDots},${decPart}`;
}

// Converte string no padrão BR (1.234,56) para número
function parseBrToNumber(str: string): number {
  const cleaned = str.replace(/\./g, '').replace(',', '.');
  return parseFloat(cleaned) || 0;
}

// Converte data ISO (YYYY-MM-DD) para BR (dd/MM/yyyy)
function formatISOToBr(iso: string): string {
  if (!iso || iso.length < 10) return '';
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

// Converte data BR (dd/MM/yyyy) para ISO (YYYY-MM-DD)
function formatBrToISO(br: string): string {
  const cleaned = br.replace(/\D/g, '');
  if (cleaned.length !== 8) return '';
  const d = cleaned.slice(0, 2);
  const m = cleaned.slice(2, 4);
  const y = cleaned.slice(4, 8);
  return `${y}-${m}-${d}`;
}

// Máscara de digitação para data dd/MM/yyyy
function maskDateBr(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
}

// Converte string dd/MM/yyyy para Date (para o Calendar)
function parseBrToDate(br: string): Date | undefined {
  if (!br || !/^\d{2}\/\d{2}\/\d{4}$/.test(br.trim())) return undefined;
  const iso = formatBrToISO(br.trim());
  if (!iso) return undefined;
  return new Date(iso + 'T12:00:00');
}

// Converte Date para dd/MM/yyyy
function formatDateToBr(date: Date): string {
  const d = String(date.getDate()).padStart(2, '0');
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const y = date.getFullYear();
  return `${d}/${m}/${y}`;
}

const expenseSchema = z.object({
  service_name: z.string().min(1, 'Nome do serviço é obrigatório'),
  description: z.string().optional(),
  expense_type: z.enum(['recurring', 'one_time'] as const),
  category_id: z.string().min(1, 'Categoria é obrigatória'),
  company_id: z.string().min(1, 'Empresa é obrigatória'),
  department_id: z.string().min(1, 'Setor é obrigatório'),
  owner_id: z.string().min(1, 'Responsável é obrigatório'),
  approver_id: z.string().optional(),
  value: z
    .string()
    .min(1, 'Informe o valor')
    .refine((s) => {
      const n = parseBrToNumber(s);
      return !Number.isNaN(n) && n > 0;
    }, 'Valor deve ser maior que zero'),
  currency: z.enum(['BRL', 'USD'] as const),
  periodicity: z.enum(['monthly', 'quarterly', 'semiannual', 'annual'] as const).optional().nullable(),
  renewal_date: z
    .string()
    .optional()
    .refine(
      (s) => !s || s.trim() === '' || /^\d{2}\/\d{2}\/\d{4}$/.test(s.trim()),
      'Use o formato dd/mm/aaaa'
    ),
  payment_method: z.enum(['credit_card', 'debit_card', 'boleto', 'pix', 'transfer'] as const).optional(),
  payment_identifier: z
    .string()
    .optional()
    .refine(
      (s) => !s || s.trim() === '' || /^\d{4}$/.test(s.trim()),
      'Informe apenas os últimos 4 dígitos do cartão'
    ),
  contracted_plan: z.string().optional(),
  user_count: z.coerce.number().optional(),
  evidence_link: z.string().url('URL inválida').optional().or(z.literal('')),
  login: z.string().optional(),
  password: z.string().optional(),
  notes: z.string().optional(),
}).superRefine((data, ctx) => {
  // Se for one_time, periodicity deve ser undefined ou null
  if (data.expense_type === 'one_time' && data.periodicity !== undefined && data.periodicity !== null) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Periodicidade não é aplicável para pagamento único',
      path: ['periodicity'],
    });
  }
});

type FormData = z.infer<typeof expenseSchema>;

interface ExpenseFormProps {
  expense?: Expense | null;
  onSuccess: () => void;
  onCancel: () => void;
}

export function ExpenseForm({ expense, onSuccess, onCancel }: ExpenseFormProps) {
  const { user } = useAuth();
  const { toast } = useToast();
  const [calendarOpen, setCalendarOpen] = useState(false);

  const { data: companies } = useQuery({
    queryKey: ['companies'],
    queryFn: companiesApi.getAll,
  });

  const { data: categories } = useQuery({
    queryKey: ['categories'],
    queryFn: categoriesApi.getAll,
  });

  const { data: users } = useQuery({
    queryKey: ['users-scoped'],
    queryFn: usersApi.getScoped,
  });

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(expenseSchema),
      defaultValues: expense
      ? {
          service_name: expense.service_name,
          description: expense.description || '',
          expense_type: expense.expense_type,
          category_id: expense.category_id,
          company_id: expense.company_id,
          department_id: expense.department_id,
          owner_id: expense.owner_id,
          approver_id: expense.owner_id,
          value: formatNumberToBr(Number(expense.value)),
          currency: expense.currency,
          periodicity: expense.expense_type === 'one_time' ? undefined : expense.periodicity,
          renewal_date: expense.renewal_date ? formatISOToBr(expense.renewal_date) : '',
          payment_method: expense.payment_method || 'credit_card',
          payment_identifier: expense.payment_identifier || '',
          contracted_plan: expense.contracted_plan || '',
          user_count: expense.user_count,
          evidence_link: expense.evidence_link || '',
          login: expense.login ?? '',
          password: expense.password ?? '',
          notes: expense.notes || '',
        }
      : {
          expense_type: 'recurring',
          currency: 'BRL',
          category_id: '',
          company_id: '',
          department_id: '',
          owner_id: '',
          value: '',
          periodicity: undefined,
          login: '',
          password: '',
          renewal_date: '',
          payment_method: undefined,
          payment_identifier: '',
          contracted_plan: '',
          user_count: undefined,
          evidence_link: '',
          notes: '',
        },
  });

  const selectedCompanyId = watch('company_id');
  const expenseType = watch('expense_type');
  const selectedOwnerId = watch('owner_id');

  // Limpar periodicity quando mudar para one_time
  useEffect(() => {
    if (expenseType === 'one_time') {
      setValue('periodicity', undefined);
    }
  }, [expenseType, setValue]);

  // Limpar owner_id quando a empresa mudar, se o owner atual não pertence à nova empresa
  useEffect(() => {
    if (selectedCompanyId && selectedOwnerId && users) {
      const currentOwner = users.find((u) => u.id === selectedOwnerId);
      if (currentOwner?.role === 'system_admin' || currentOwner?.role === 'finance_admin') return;
      const ownerBelongsToCompany = currentOwner?.companies?.some((c) => c.id === selectedCompanyId) ?? false;
      if (!ownerBelongsToCompany) {
        setValue('owner_id', '');
      }
    }
  }, [selectedCompanyId, users, selectedOwnerId, setValue]);

  const { data: departments } = useQuery({
    queryKey: ['departments', selectedCompanyId],
    queryFn: () => departmentsApi.getAll(selectedCompanyId),
    enabled: !!selectedCompanyId,
  });

  const createMutation = useMutation({
    mutationFn: (data: ExpenseFormData) => expensesApi.create(data),
    onSuccess,
    onError: (err: AxiosError<{ detail?: string | string[] | { msg?: string }[] }>) => {
      const detail = err.response?.data?.detail;
      let message = err.message;
      if (Array.isArray(detail)) {
        message = detail
          .map((d) => (typeof d === 'object' && d?.msg ? d.msg : String(d)))
          .join('; ');
      } else if (typeof detail === 'string') {
        message = detail;
      }
      toast({
        title: 'Erro ao criar despesa',
        description: message,
        variant: 'destructive',
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: ExpenseUpdatePayload) => expensesApi.update(expense!.id, data),
    onSuccess,
    onError: (err: AxiosError<{ detail?: string | string[] | { msg?: string }[] }>) => {
      const detail = err.response?.data?.detail;
      let message = err.message;
      if (Array.isArray(detail)) {
        message = detail
          .map((d) => (typeof d === 'object' && d?.msg ? d.msg : String(d)))
          .join('; ');
      } else if (typeof detail === 'string') {
        message = detail;
      }
      toast({
        title: 'Erro ao atualizar despesa',
        description: message,
        variant: 'destructive',
      });
    },
  });

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  // Helper function para remover campos undefined
  const removeUndefined = <T extends Record<string, any>>(obj: T): Partial<T> => {
    return Object.fromEntries(
      Object.entries(obj).filter(([_, value]) => value !== undefined)
    ) as Partial<T>;
  };

  const onSubmit = (data: FormData) => {
    console.log('onSubmit chamado com dados:', data);
    const valueNum = parseBrToNumber(data.value);
    
    if (expense) {
      console.log('Modo atualização - expense ID:', expense.id);
      // Para atualização, sempre enviar TODOS os campos obrigatórios
      // e campos opcionais apenas se tiverem valores (não undefined/null)
      const updateData: ExpenseUpdatePayload = {
        // Campos obrigatórios - sempre enviados para garantir atualização
        service_name: data.service_name.trim(),
        expense_type: data.expense_type,
        category_id: data.category_id,
        company_id: data.company_id,
        department_id: data.department_id,
        owner_id: data.owner_id,
        approver_id: data.owner_id,
        value: valueNum,
        currency: data.currency,
        payment_method: data.payment_method || 'credit_card',
      };

      // Adicionar campos opcionais apenas se tiverem valores definidos
      const description = data.description?.trim();
      if (description !== undefined && description !== '') {
        updateData.description = description;
      }
      
      // Periodicity só é enviado se for recurring e tiver valor
      if (data.expense_type === 'recurring' && data.periodicity !== undefined && data.periodicity !== null) {
        updateData.periodicity = data.periodicity;
      }
      
      const renewalDate = data.renewal_date?.trim();
      if (renewalDate && renewalDate !== '') {
        updateData.renewal_date = formatBrToISO(renewalDate);
      }
      
      const paymentIdentifier = data.payment_identifier?.trim();
      if (paymentIdentifier !== undefined && paymentIdentifier !== '') {
        updateData.payment_identifier = paymentIdentifier;
      }
      
      const contractedPlan = data.contracted_plan?.trim();
      if (contractedPlan !== undefined && contractedPlan !== '') {
        updateData.contracted_plan = contractedPlan;
      }
      
      if (data.user_count !== undefined && data.user_count !== null) {
        updateData.user_count = data.user_count;
      }
      
      const evidenceLink = data.evidence_link?.trim();
      if (evidenceLink !== undefined && evidenceLink !== '') {
        updateData.evidence_link = evidenceLink;
      }
      
      const login = data.login?.trim();
      if (login !== undefined && login !== '') {
        updateData.login = login;
      }
      
      const password = data.password?.trim();
      if (password !== undefined && password !== '') {
        updateData.password = password;
      }
      
      const notes = data.notes?.trim();
      if (notes !== undefined && notes !== '') {
        updateData.notes = notes;
      }

      console.log('Enviando dados de atualização:', updateData);
      updateMutation.mutate(updateData);
    } else {
      // Para criação, usar todos os campos
      const formData: ExpenseFormData = {
        service_name: data.service_name.trim(),
        expense_type: data.expense_type,
        category_id: data.category_id,
        company_id: data.company_id,
        department_id: data.department_id,
        owner_id: data.owner_id,
        approver_id: data.owner_id,
        value: valueNum,
        currency: data.currency,
        description: data.description?.trim() || undefined,
        periodicity: data.periodicity,
        renewal_date: data.renewal_date?.trim() ? formatBrToISO(data.renewal_date.trim()) : undefined,
        payment_method: data.payment_method || 'credit_card',
        payment_identifier: data.payment_identifier?.trim() || undefined,
        contracted_plan: data.contracted_plan?.trim() || undefined,
        user_count: data.user_count,
        evidence_link: data.evidence_link?.trim() || undefined,
        login: data.login?.trim() || undefined,
        password: data.password?.trim() || undefined,
        notes: data.notes?.trim() || undefined,
      };
      createMutation.mutate(formData);
    }
  };

  const onInvalid = (errors: any) => {
    console.error('Erros de validação:', errors);
    const errorFields = Object.keys(errors);
    toast({
      title: 'Erro de validação',
      description: `Por favor, verifique os seguintes campos: ${errorFields.join(', ')}`,
      variant: 'destructive',
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit, onInvalid)} className="space-y-6">
      {/* Basic Information */}
      <div className="space-y-4">
        <h3 className="font-medium text-lg border-b pb-2">Informações Básicas</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <Label htmlFor="service_name">Nome do Serviço *</Label>
            <Input
              id="service_name"
              {...register('service_name')}
              placeholder="Ex: AWS Cloud Services"
            />
            {errors.service_name && (
              <p className="text-sm text-destructive mt-1">{errors.service_name.message}</p>
            )}
          </div>

          <div className="col-span-2">
            <Label htmlFor="description">Descrição</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Descrição do serviço..."
              rows={2}
            />
          </div>

          <div>
            <Label htmlFor="expense_type">Tipo *</Label>
            <Select
              value={expenseType ?? ''}
              onValueChange={(v) => setValue('expense_type', v as ExpenseType)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecione" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="recurring">Recorrente</SelectItem>
                <SelectItem value="one_time">Único</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="category_id">Categoria *</Label>
            <Select
              value={watch('category_id') ?? ''}
              onValueChange={(v) => setValue('category_id', v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecione" />
              </SelectTrigger>
              <SelectContent>
                {categories?.filter(c => c.is_active).map((category) => (
                  <SelectItem key={category.id} value={category.id}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.category_id && (
              <p className="text-sm text-destructive mt-1">{errors.category_id.message}</p>
            )}
          </div>
        </div>
      </div>

      {/* Location */}
      <div className="space-y-4">
        <h3 className="font-medium text-lg border-b pb-2">Localização</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="company_id">Empresa *</Label>
            <Select
              value={watch('company_id') ?? ''}
              onValueChange={(v) => {
                setValue('company_id', v);
                setValue('department_id', '');
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecione" />
              </SelectTrigger>
              <SelectContent>
                {(user?.role === 'leader' && user.companies
                  ? companies?.filter((c) => c.is_active && user.companies?.some((uc) => uc.id === c.id))
                  : companies?.filter((c) => c.is_active)
                )?.map((company) => (
                  <SelectItem key={company.id} value={company.id}>
                    {company.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.company_id && (
              <p className="text-sm text-destructive mt-1">{errors.company_id.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="department_id">Setor *</Label>
            <Select
              value={watch('department_id') ?? ''}
              onValueChange={(v) => setValue('department_id', v)}
              disabled={!selectedCompanyId}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecione" />
              </SelectTrigger>
              <SelectContent>
                {departments?.filter((d) => d.is_active)?.map((department) => (
                  <SelectItem key={department.id} value={department.id}>
                    {department.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.department_id && (
              <p className="text-sm text-destructive mt-1">{errors.department_id.message}</p>
            )}
          </div>
        </div>
      </div>

      {/* Responsável (também é o validador) */}
      <div className="space-y-4">
        <h3 className="font-medium text-lg border-b pb-2">Responsável</h3>
        <div>
          <Label htmlFor="owner_id">Responsável *</Label>
          <Select
            value={watch('owner_id') ?? ''}
            onValueChange={(v) => setValue('owner_id', v)}
            disabled={!selectedCompanyId}
          >
            <SelectTrigger>
              <SelectValue placeholder={selectedCompanyId ? "Selecione" : "Selecione uma empresa primeiro"} />
            </SelectTrigger>
            <SelectContent>
              {users
                ?.filter((u) => {
                  if (!u.is_active) return false;
                  // Se não há empresa selecionada, não mostrar ninguém
                  if (!selectedCompanyId) return false;
                  // Admins podem ser responsáveis em qualquer empresa
                  if (u.role === 'system_admin' || u.role === 'finance_admin') return true;
                  // Para outros, verificar se pertencem à empresa
                  return u.companies?.some((c) => c.id === selectedCompanyId) ?? false;
                })
                ?.map((u) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
          {errors.owner_id && (
            <p className="text-sm text-destructive mt-1">{errors.owner_id.message}</p>
          )}
          {selectedCompanyId && users && users.filter((u) => u.is_active && ((u.role === 'system_admin' || u.role === 'finance_admin') || (u.companies?.some((c) => c.id === selectedCompanyId) ?? false))).length === 0 && (
            <p className="text-sm text-muted-foreground mt-1">
              Nenhum responsável disponível para esta empresa
            </p>
          )}
        </div>
      </div>

      {/* Values */}
      <div className="space-y-4">
        <h3 className="font-medium text-lg border-b pb-2">Valores</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="value">Valor *</Label>
            <Controller
              name="value"
              control={control}
              render={({ field }) => (
                <Input
                  id="value"
                  type="text"
                  inputMode="decimal"
                  placeholder="0,00"
                  {...field}
                  onChange={(e) => {
                    let v = e.target.value.replace(/[^\d,]/g, '');
                    const parts = v.split(',');
                    if (parts.length > 2) v = parts[0] + ',' + parts.slice(1).join('');
                    if (parts[1]?.length > 2) v = parts[0] + ',' + parts[1].slice(0, 2);
                    field.onChange(v);
                  }}
                  onBlur={() => {
                    const num = parseBrToNumber(field.value);
                    if (!Number.isNaN(num) && num >= 0) {
                      field.onChange(formatNumberToBr(num));
                    }
                    field.onBlur();
                  }}
                />
              )}
            />
            {errors.value && (
              <p className="text-sm text-destructive mt-1">{errors.value.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="currency">Moeda *</Label>
            <Select
              value={watch('currency') ?? ''}
              onValueChange={(v) => setValue('currency', v as Currency)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Moeda" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BRL">BRL (R$)</SelectItem>
                <SelectItem value="USD">USD ($)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {expenseType === 'recurring' && (
            <>
              <div>
                <Label htmlFor="periodicity">Periodicidade</Label>
                <Select
                  value={watch('periodicity') ?? ''}
                  onValueChange={(v) => setValue('periodicity', v ? (v as Periodicity) : undefined)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="monthly">Mensal</SelectItem>
                    <SelectItem value="quarterly">Trimestral</SelectItem>
                    <SelectItem value="semiannual">Semestral</SelectItem>
                    <SelectItem value="annual">Anual</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="renewal_date">Data de Renovação</Label>
                <Controller
                  name="renewal_date"
                  control={control}
                  render={({ field }) => (
                    <Popover open={calendarOpen} onOpenChange={setCalendarOpen}>
                      <PopoverTrigger asChild>
                        <Button
                          id="renewal_date"
                          variant="outline"
                          className="w-full justify-start text-left font-normal h-10"
                        >
                          <CalendarIcon className="mr-2 h-4 w-4" />
                          {field.value ? field.value : 'Selecione a data'}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                          mode="single"
                          selected={parseBrToDate(field.value) ?? undefined}
                          onSelect={(date) => {
                            if (date) {
                              field.onChange(formatDateToBr(date));
                              setCalendarOpen(false);
                            }
                          }}
                          locale={ptBR}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                  )}
                />
                {errors.renewal_date && (
                  <p className="text-sm text-destructive mt-1">{errors.renewal_date.message}</p>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Payment */}
      <div className="space-y-4">
        <h3 className="font-medium text-lg border-b pb-2">Pagamento</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="payment_method">Método de Pagamento</Label>
            <Select
              value={watch('payment_method') ?? ''}
              onValueChange={(v) => setValue('payment_method', v ? (v as PaymentMethod) : undefined)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecione" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="credit_card">Cartão de Crédito</SelectItem>
                <SelectItem value="debit_card">Cartão de Débito</SelectItem>
                <SelectItem value="transfer">Transferência Bancária</SelectItem>
                <SelectItem value="boleto">Boleto</SelectItem>
                <SelectItem value="pix">PIX</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="payment_identifier">Últimos 4 dígitos do cartão</Label>
            <Controller
              name="payment_identifier"
              control={control}
              render={({ field }) => (
                <Input
                  id="payment_identifier"
                  {...field}
                  placeholder="Ex: 1234"
                  maxLength={4}
                  pattern="[0-9]*"
                  inputMode="numeric"
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, '').slice(0, 4);
                    field.onChange(value);
                  }}
                />
              )}
            />
            {errors.payment_identifier && (
              <p className="text-sm text-destructive mt-1">{errors.payment_identifier.message}</p>
            )}
          </div>
        </div>
      </div>

      {/* Details */}
      <div className="space-y-4">
        <h3 className="font-medium text-lg border-b pb-2">Detalhes</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="contracted_plan">Plano Contratado</Label>
            <Input
              id="contracted_plan"
              {...register('contracted_plan')}
              placeholder="Ex: Enterprise"
            />
          </div>

          <div>
            <Label htmlFor="user_count">Quantidade de Usuários</Label>
            <Input
              id="user_count"
              type="number"
              {...register('user_count', { valueAsNumber: true })}
              placeholder="0"
            />
          </div>

          <div className="col-span-2">
            <Label htmlFor="evidence_link">Link de Evidência</Label>
            <Input
              id="evidence_link"
              type="url"
              {...register('evidence_link')}
              placeholder="https://..."
            />
            {errors.evidence_link && (
              <p className="text-sm text-destructive mt-1">{errors.evidence_link.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="login">Login</Label>
            <Input
              id="login"
              {...register('login')}
              placeholder="Ex: usuario@empresa.com ou N/A"
            />
            {errors.login && (
              <p className="text-sm text-destructive mt-1">{errors.login.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="password">Senha</Label>
            <Input
              id="password"
              type="password"
              {...register('password')}
              placeholder="Ex: senha123 ou N/A"
            />
            {errors.password && (
              <p className="text-sm text-destructive mt-1">{errors.password.message}</p>
            )}
          </div>

          <div className="col-span-2">
            <Label htmlFor="notes">Notas</Label>
            <Textarea
              id="notes"
              {...register('notes')}
              placeholder="Observações adicionais..."
              rows={3}
            />
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" className="nitro-btn-primary" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          {expense ? 'Salvar Alterações' : 'Criar Despesa'}
        </Button>
      </div>
    </form>
  );
}
