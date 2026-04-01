// Tipos alinhados à API do backend (IDs são UUID string)

// User & Auth Types
export type UserRole = 'finance_admin' | 'system_admin' | 'leader';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  phone?: string;
  is_active: boolean;
  departments: Department[];
  companies?: { id: string; name: string }[];
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

// Company & Department Types
export interface Company {
  id: string;
  name: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Department {
  id: string;
  name: string;
  company_id: string;
  company?: Company;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

// Category Type
export interface Category {
  id: string;
  name: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

// Expense Types (backend)
export type ExpenseType = 'recurring' | 'one_time';
export type ExpenseStatus = 'active' | 'cancelled';
export type ReviewStatus = 'normal' | 'review';
export type Periodicity = 'monthly' | 'quarterly' | 'semiannual' | 'annual';
export type Currency = 'BRL' | 'USD';
export type PaymentMethod = 'credit_card' | 'debit_card' | 'boleto' | 'pix' | 'transfer';

export interface Expense {
  id: string;
  code: string;
  service_name: string;
  description?: string;
  expense_type: ExpenseType;
  category_id: string;
  category?: Category;
  company_id: string;
  company?: Company;
  department_id: string;
  department?: Department;
  owner_id: string;
  owner?: User;
  approver_id: string;
  approver?: User;
  value: number;
  currency: Currency;
  value_brl: number;
  exchange_rate?: number;
  exchange_rate_date?: string;
  periodicity?: Periodicity;
  renewal_date?: string;
  payment_method: PaymentMethod;
  payment_identifier?: string;
  contracted_plan?: string;
  user_count?: number;
  evidence_link?: string;
  login?: string;
  password?: string;
  notes?: string;
  status: ExpenseStatus;
  review_status?: ReviewStatus;
  cancellation_month?: string;
  charged_when_cancelled?: boolean;
  created_at: string;
  updated_at: string;
  created_by?: { id: string; name: string; email: string };
  cancelled_at?: string;
  cancelled_by?: { id: string; name: string; email: string };
  validations?: ExpenseValidationLogItem[];
}

export interface ExpenseValidationLogItem {
  validation_month: string;
  status: string;
  validated_at?: string;
  validator?: { id: string; name: string; email: string };
}

export interface ExpenseFormData {
  service_name: string;
  description?: string;
  expense_type: ExpenseType;
  category_id: string;
  company_id: string;
  department_id: string;
  owner_id: string;
  approver_id?: string;
  value: number;
  currency: Currency;
  periodicity?: Periodicity;
  renewal_date?: string;
  payment_method: PaymentMethod;
  payment_identifier?: string;
  contracted_plan?: string;
  user_count?: number;
  evidence_link?: string;
  login?: string;
  password?: string;
  notes?: string;
}

/** Payload para atualização de despesa (inclui status para alteração na lista) */
export type ExpenseUpdatePayload = Partial<ExpenseFormData> & { status?: ExpenseStatus; review_status?: ReviewStatus };

// Validation Types (backend: expense_validations)
export type ValidationStatus = 'pending' | 'approved' | 'rejected';

export interface ExpenseValidation {
  id?: string; // Opcional para validações previstas (não criadas)
  expense_id: string;
  validator_id?: string; // Opcional - preenchido apenas quando alguém valida
  validation_month: string; // YYYY-MM-DD (primeiro dia do mês)
  status: ValidationStatus;
  validated_at?: string;
  is_overdue: boolean; // Indica se a validação está atrasada (>4 dias do início do mês)
  is_predicted?: boolean; // Indica se é uma validação prevista (não criada)
  created_at?: string; // Opcional para validações previstas
  updated_at?: string;
  expense?: Expense;
  validator?: User; // Usuário que validou (se validator_id estiver preenchido)
}

export interface CreateMonthlyValidationsResponse {
  message: string;
  count: number;
  month: string; // YYYY-MM-DD
}

// Alert Types (backend)
export type AlertType = 'validation_pending' | 'validation_overdue' | 'renewal_upcoming' | 'renewal_due' | 'expense_cancellation';
export type AlertStatus = 'pending' | 'sent' | 'failed' | 'read';

export interface Alert {
  id: string;
  alert_type: AlertType;
  title: string;
  message: string;
  recipient_id: string;
  channel: string;
  status: AlertStatus;
  expense_id?: string;
  validation_id?: string;
  sent_at?: string;
  read_at?: string;
  error_message?: string;
  created_at: string;
  updated_at?: string;
  recipient?: User;
  expense?: Expense;
}

// Dashboard Stats
export interface DashboardStats {
  total_expenses_value: number;
  monthly_expenses_value: number;
  average_expense_value: number;
  pending_validations: number;
  overdue_validations: number;
  unread_alerts: number;
  active_expenses: number;
  recurring_expenses: number;
  one_time_expenses: number;
  upcoming_renewals: number;
  cancelled_expenses_value: number;
}

export interface CategoryExpenseItem {
  category_id: string;
  category_name: string;
  total_value: number;
  count: number;
  percentage: number;
}

export interface CategoryExpenseResponse {
  items: CategoryExpenseItem[];
  total: number;
}

export interface CompanyExpenseItem {
  company_id: string;
  company_name: string;
  total_value: number;
  count: number;
  percentage: number;
}

export interface CompanyExpenseResponse {
  items: CompanyExpenseItem[];
  total: number;
}

export interface DepartmentExpenseItem {
  department_id: string;
  department_name: string;
  company_name: string;
  total_value: number;
  count: number;
  percentage: number;
}

export interface DepartmentExpenseResponse {
  items: DepartmentExpenseItem[];
  total: number;
}

export interface TimelineDataPoint {
  month: string; // YYYY-MM
  total_value: number;
  count: number;
}

export interface TimelineDataResponse {
  data: TimelineDataPoint[];
}

export interface TopExpenseItem {
  expense_id: string;
  service_name: string;
  category_name: string;
  company_name: string;
  department_name: string;
  value: number;
  currency: Currency;
  value_brl: number;
  status: ExpenseStatus;
}

export interface TopExpenseResponse {
  items: TopExpenseItem[];
}

export interface StatusDistributionItem {
  status: ExpenseStatus;
  count: number;
  total_value: number;
  percentage: number;
}

export interface StatusDistributionResponse {
  items: StatusDistributionItem[];
  total_count: number;
  total_value: number;
}

export interface UpcomingRenewalItem {
  expense_id: string;
  service_name: string;
  renewal_date: string;
  value: number;
  currency: Currency;
  value_brl: number;
  days_until_renewal: number;
}

export interface UpcomingRenewalsResponse {
  items: UpcomingRenewalItem[];
  count: number;
}

// API Response Types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Filter Types
export interface ExpenseFilters {
  company_ids?: string[];
  department_ids?: string[];
  owner_ids?: string[];
  category_ids?: string[];
  status?: ExpenseStatus[];
  expense_type?: ExpenseType[];
  service_name?: string;
}

export interface AlertFilters {
  status?: AlertStatus;
  limit?: number;
}

export interface DashboardFilters {
  company_id?: string;
  department_id?: string;
  month?: string; // YYYY-MM para validações pendentes
}
