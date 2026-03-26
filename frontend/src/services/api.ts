import { apiClient, USE_MOCK } from '@/lib/api-client';
import {
  mockUsers,
  mockCompanies,
  mockDepartments,
  mockCategories,
  mockExpenses,
  mockValidations,
  mockAlerts,
  mockDashboardStats,
  delay,
} from '@/lib/mock-data';
import type {
  User,
  Company,
  Department,
  Category,
  Expense,
  ExpenseFormData,
  ExpenseUpdatePayload,
  ExpenseValidation,
  Alert,
  DashboardStats,
  AuthResponse,
  LoginCredentials,
  ExpenseFilters,
  AlertFilters,
  DashboardFilters,
  CategoryExpenseResponse,
  CompanyExpenseResponse,
  DepartmentExpenseResponse,
  TimelineDataResponse,
  TopExpenseResponse,
  StatusDistributionResponse,
  UpcomingRenewalsResponse,
} from '@/types';

// Auth API
export const authApi = {
  login: async (credentials: LoginCredentials): Promise<AuthResponse> => {
    if (USE_MOCK) {
      await delay();
      const user = mockUsers.find(u => u.email === credentials.email);
      if (user && credentials.password === 'password123') {
        return { access_token: 'mock_token_' + user.id, token_type: 'bearer' };
      }
      throw new Error('Invalid credentials');
    }
    const { data } = await apiClient.post<AuthResponse>('/auth/login', credentials);
    return data;
  },

  getCurrentUser: async (): Promise<User> => {
    if (USE_MOCK) {
      await delay();
      const token = localStorage.getItem('nitro_token');
      const userId = token ? token.replace('mock_token_', '') : '1';
      const user = mockUsers.find(u => u.id === userId);
      if (user) return user;
      throw new Error('User not found');
    }
    const { data } = await apiClient.get<User>('/users/me');
    return data;
  },
};

// Users API
export const usersApi = {
  getAll: async (): Promise<User[]> => {
    if (USE_MOCK) {
      await delay();
      return mockUsers;
    }
    const { data } = await apiClient.get<User[]>('/users');
    return data;
  },

  getScoped: async (): Promise<User[]> => {
    if (USE_MOCK) {
      await delay();
      return mockUsers.filter(
        (u) => u.is_active && (u.role === 'leader' || u.role === 'finance_admin' || u.role === 'system_admin')
      );
    }
    const { data } = await apiClient.get<User[]>('/users/scoped');
    return data;
  },

  getById: async (id: string): Promise<User> => {
    if (USE_MOCK) {
      await delay();
      const user = mockUsers.find(u => u.id === id);
      if (user) return user;
      throw new Error('User not found');
    }
    const { data } = await apiClient.get<User>(`/users/${id}`);
    return data;
  },

  create: async (userData: Partial<User> & { password: string; company_ids?: string[] }): Promise<User> => {
    if (USE_MOCK) {
      await delay();
      const newUser: User = {
        id: String(mockUsers.length + 1),
        name: userData.name || '',
        email: userData.email || '',
        role: userData.role || 'leader',
        phone: userData.phone,
        is_active: true,
        departments: [],
      };
      mockUsers.push(newUser);
      return newUser;
    }
    const { data } = await apiClient.post<User>('/users', userData);
    return data;
  },

  update: async (id: string, userData: Partial<User> & { password?: string; company_ids?: string[] }): Promise<User> => {
    if (USE_MOCK) {
      await delay();
      const index = mockUsers.findIndex(u => u.id === id);
      if (index !== -1) {
        mockUsers[index] = { ...mockUsers[index], ...userData };
        return mockUsers[index];
      }
      throw new Error('User not found');
    }
    const { data } = await apiClient.put<User>(`/users/${id}`, userData);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    if (USE_MOCK) {
      await delay();
      const index = mockUsers.findIndex(u => u.id === id);
      if (index !== -1) {
        mockUsers.splice(index, 1);
        return;
      }
      throw new Error('User not found');
    }
    await apiClient.delete(`/users/${id}`);
  },
};

// Companies API
export const companiesApi = {
  getAll: async (): Promise<Company[]> => {
    if (USE_MOCK) {
      await delay();
      return mockCompanies;
    }
    const { data } = await apiClient.get<Company[]>('/companies/me');
    return data;
  },

  getById: async (id: string): Promise<Company> => {
    if (USE_MOCK) {
      await delay();
      const company = mockCompanies.find(c => c.id === id);
      if (company) return company;
      throw new Error('Company not found');
    }
    const { data } = await apiClient.get<Company>(`/companies/${id}`);
    return data;
  },

  create: async (companyData: Partial<Company>): Promise<Company> => {
    if (USE_MOCK) {
      await delay();
      const newCompany: Company = {
        id: String(mockCompanies.length + 1),
        name: companyData.name || '',
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      mockCompanies.push(newCompany);
      return newCompany;
    }
    const { data } = await apiClient.post<Company>('/companies', companyData);
    return data;
  },

  update: async (id: string, companyData: Partial<Company>): Promise<Company> => {
    if (USE_MOCK) {
      await delay();
      const index = mockCompanies.findIndex(c => c.id === id);
      if (index !== -1) {
        mockCompanies[index] = { ...mockCompanies[index], ...companyData, updated_at: new Date().toISOString() };
        return mockCompanies[index];
      }
      throw new Error('Company not found');
    }
    const { data } = await apiClient.put<Company>(`/companies/${id}`, companyData);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    if (USE_MOCK) {
      await delay();
      const index = mockCompanies.findIndex(c => c.id === id);
      if (index !== -1) {
        mockCompanies.splice(index, 1);
        return;
      }
      throw new Error('Company not found');
    }
    await apiClient.delete(`/companies/${id}`);
  },
};

// Departments API
export const departmentsApi = {
  getAll: async (companyId?: string): Promise<Department[]> => {
    if (USE_MOCK) {
      await delay();
      if (companyId) {
        return mockDepartments.filter(d => d.company_id === companyId);
      }
      return mockDepartments;
    }
    // Usar /departments/me que funciona para todos os usuários e retorna setores baseado no escopo
    // Para System Admin e Finance Admin retorna todos os setores
    const params = companyId ? { company_id: companyId } : {};
    const { data } = await apiClient.get<Department[]>('/departments/me', { params });
    return data;
  },

  getById: async (id: string): Promise<Department> => {
    if (USE_MOCK) {
      await delay();
      const department = mockDepartments.find(d => d.id === id);
      if (department) return department;
      throw new Error('Department not found');
    }
    const { data } = await apiClient.get<Department>(`/departments/${id}`);
    return data;
  },

  create: async (departmentData: Partial<Department>): Promise<Department> => {
    if (USE_MOCK) {
      await delay();
      const company = mockCompanies.find(c => c.id === departmentData.company_id);
      const newDepartment: Department = {
        id: String(mockDepartments.length + 1),
        name: departmentData.name || '',
        company_id: departmentData.company_id || '1',
        company,
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      mockDepartments.push(newDepartment);
      return newDepartment;
    }
    const { data } = await apiClient.post<Department>('/departments', departmentData);
    return data;
  },

  update: async (id: string, departmentData: Partial<Department>): Promise<Department> => {
    if (USE_MOCK) {
      await delay();
      const index = mockDepartments.findIndex(d => d.id === id);
      if (index !== -1) {
        mockDepartments[index] = { ...mockDepartments[index], ...departmentData, updated_at: new Date().toISOString() };
        return mockDepartments[index];
      }
      throw new Error('Department not found');
    }
    const { data } = await apiClient.put<Department>(`/departments/${id}`, departmentData);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    if (USE_MOCK) {
      await delay();
      const index = mockDepartments.findIndex(d => d.id === id);
      if (index !== -1) {
        mockDepartments.splice(index, 1);
        return;
      }
      throw new Error('Department not found');
    }
    await apiClient.delete(`/departments/${id}`);
  },
};

// Categories API
export const categoriesApi = {
  getAll: async (): Promise<Category[]> => {
    if (USE_MOCK) {
      await delay();
      return mockCategories;
    }
    // Usar /categories/me que funciona para todos os usuários autenticados
    const { data } = await apiClient.get<Category[]>('/categories/me');
    return data;
  },

  getById: async (id: string): Promise<Category> => {
    if (USE_MOCK) {
      await delay();
      const category = mockCategories.find(c => c.id === id);
      if (category) return category;
      throw new Error('Category not found');
    }
    const { data } = await apiClient.get<Category>(`/categories/${id}`);
    return data;
  },

  create: async (categoryData: Partial<Category>): Promise<Category> => {
    if (USE_MOCK) {
      await delay();
      const newCategory: Category = {
        id: String(mockCategories.length + 1),
        name: categoryData.name || '',
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      mockCategories.push(newCategory);
      return newCategory;
    }
    const { data } = await apiClient.post<Category>('/categories', categoryData);
    return data;
  },

  update: async (id: string, categoryData: Partial<Category>): Promise<Category> => {
    if (USE_MOCK) {
      await delay();
      const index = mockCategories.findIndex(c => c.id === id);
      if (index !== -1) {
        mockCategories[index] = { ...mockCategories[index], ...categoryData, updated_at: new Date().toISOString() };
        return mockCategories[index];
      }
      throw new Error('Category not found');
    }
    const { data } = await apiClient.put<Category>(`/categories/${id}`, categoryData);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    if (USE_MOCK) {
      await delay();
      const index = mockCategories.findIndex(c => c.id === id);
      if (index !== -1) {
        mockCategories.splice(index, 1);
        return;
      }
      throw new Error('Category not found');
    }
    await apiClient.delete(`/categories/${id}`);
  },
};

// Expenses API
export const expensesApi = {
  getAll: async (filters?: ExpenseFilters): Promise<Expense[]> => {
    if (USE_MOCK) {
      await delay();
      let expenses = [...mockExpenses];
      if (filters?.company_ids?.length) {
        expenses = expenses.filter(e => filters.company_ids!.includes(e.company_id));
      }
      if (filters?.department_ids?.length) {
        expenses = expenses.filter(e => filters.department_ids!.includes(e.department_id));
      }
      if (filters?.owner_ids?.length) {
        expenses = expenses.filter(e => filters.owner_ids!.includes(e.owner_id));
      }
      if (filters?.category_ids?.length) {
        expenses = expenses.filter(e => filters.category_ids!.includes(e.category_id));
      }
      if (filters?.status?.length) {
        expenses = expenses.filter(e => filters.status!.includes(e.status));
      }
      if (filters?.expense_type?.length) {
        expenses = expenses.filter(e => filters.expense_type!.includes(e.expense_type));
      }
      if (filters?.service_name) {
        const term = filters.service_name.toLowerCase();
        expenses = expenses.filter(e =>
          e.service_name.toLowerCase().includes(term)
        );
      }
      expenses.sort((a, b) =>
        new Date(b.created_at ?? 0).getTime() - new Date(a.created_at ?? 0).getTime()
      );
      return expenses;
    }
    const params = new URLSearchParams();
    filters?.company_ids?.forEach((id) => params.append('company_ids', id));
    filters?.department_ids?.forEach((id) => params.append('department_ids', id));
    filters?.owner_ids?.forEach((id) => params.append('owner_ids', id));
    filters?.category_ids?.forEach((id) => params.append('category_ids', id));
    filters?.status?.forEach((s) => params.append('status', s));
    filters?.expense_type?.forEach((t) => params.append('expense_type', t));
    if (filters?.service_name) params.append('service_name', filters.service_name);
    const { data } = await apiClient.get<Expense[]>(`/expenses?${params.toString()}`);
    return data;
  },

  getById: async (id: string): Promise<Expense> => {
    if (USE_MOCK) {
      await delay();
      const expense = mockExpenses.find(e => e.id === id);
      if (expense) return expense;
      throw new Error('Expense not found');
    }
    const { data } = await apiClient.get<Expense>(`/expenses/${id}`);
    return data;
  },

  create: async (expenseData: ExpenseFormData): Promise<Expense> => {
    if (USE_MOCK) {
      await delay();
      const newExpense: Expense = {
        id: String(mockExpenses.length + 1),
        ...expenseData,
        status: 'active',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      mockExpenses.push(newExpense);
      return newExpense;
    }
    const { data } = await apiClient.post<Expense>('/expenses', expenseData);
    return data;
  },

  update: async (id: string, expenseData: ExpenseUpdatePayload): Promise<Expense> => {
    if (USE_MOCK) {
      await delay();
      const index = mockExpenses.findIndex(e => e.id === id);
      if (index !== -1) {
        mockExpenses[index] = { ...mockExpenses[index], ...expenseData, updated_at: new Date().toISOString() };
        return mockExpenses[index];
      }
      throw new Error('Expense not found');
    }
    const { data } = await apiClient.put<Expense>(`/expenses/${id}`, expenseData);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    if (USE_MOCK) {
      await delay();
      const index = mockExpenses.findIndex(e => e.id === id);
      if (index !== -1) {
        mockExpenses.splice(index, 1);
        return;
      }
      throw new Error('Expense not found');
    }
    await apiClient.delete(`/expenses/${id}`);
  },

  cancel: async (id: string, payload: { charged_this_month: boolean; cancellation_month?: string }): Promise<Expense> => {
    if (USE_MOCK) {
      await delay();
      const index = mockExpenses.findIndex(e => e.id === id);
      if (index !== -1) {
        mockExpenses[index] = { ...mockExpenses[index], status: 'cancelled', updated_at: new Date().toISOString() };
        return mockExpenses[index];
      }
      throw new Error('Expense not found');
    }
    const { data } = await apiClient.post<Expense>(`/expenses/${id}/cancel`, payload);
    return data;
  },
};

// Validations API
export const validationsApi = {
  getPending: async (month?: string): Promise<ExpenseValidation[]> => {
    if (USE_MOCK) {
      await delay();
      let validations = mockValidations.filter(v => v.status === 'pending');
      if (month) {
        validations = validations.filter(v => v.validation_month === month);
      }
      return validations;
    }
    const params = month ? { month } : {};
    const { data } = await apiClient.get<ExpenseValidation[]>('/expense-validations/pending', { params });
    return data;
  },

  getHistory: async (filters?: { status?: string; month?: string; expense_id?: string }): Promise<ExpenseValidation[]> => {
    if (USE_MOCK) {
      await delay();
      let validations = [...mockValidations];
      if (filters?.status) {
        validations = validations.filter(v => v.status === filters.status);
      }
      if (filters?.month) {
        validations = validations.filter(v => v.validation_month === filters.month);
      }
      if (filters?.expense_id) {
        validations = validations.filter(v => v.expense_id === filters.expense_id);
      }
      return validations;
    }
    const { data } = await apiClient.get<ExpenseValidation[]>('/expense-validations/history', { params: filters });
    return data;
  },

  getPredicted: async (month: string): Promise<ExpenseValidation[]> => {
    if (USE_MOCK) {
      await delay();
      // Mock: retornar despesas recorrentes que teriam validação
      return [];
    }
    const { data } = await apiClient.get<ExpenseValidation[]>(
      '/expense-validations/predicted',
      { params: { month: `${month}-01` } }
    );
    return data;
  },

  approve: async (id: string): Promise<ExpenseValidation> => {
    if (USE_MOCK) {
      await delay();
      const index = mockValidations.findIndex(v => v.id === id);
      if (index !== -1) {
        mockValidations[index] = {
          ...mockValidations[index],
          status: 'approved',
          validated_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        return mockValidations[index];
      }
      throw new Error('Validation not found');
    }
    const { data } = await apiClient.post<ExpenseValidation>(`/expense-validations/${id}/approve`);
    return data;
  },

  reject: async (id: string, body?: { charged_this_month: boolean }): Promise<ExpenseValidation> => {
    if (USE_MOCK) {
      await delay();
      const index = mockValidations.findIndex(v => v.id === id);
      if (index !== -1) {
        mockValidations[index] = {
          ...mockValidations[index],
          status: 'rejected',
          validated_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        return mockValidations[index];
      }
      throw new Error('Validation not found');
    }
    const { data } = await apiClient.post<ExpenseValidation>(`/expense-validations/${id}/reject`, body ?? { charged_this_month: false });
    return data;
  },

  adminCancelApproval: async (id: string): Promise<ExpenseValidation> => {
    if (USE_MOCK) {
      await delay();
      const index = mockValidations.findIndex(v => v.id === id);
      if (index !== -1) {
        mockValidations[index] = {
          ...mockValidations[index],
          status: 'rejected',
          validated_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        return mockValidations[index];
      }
      throw new Error('Validation not found');
    }
    const { data } = await apiClient.post<ExpenseValidation>(`/expense-validations/${id}/admin-cancel-approval`);
    return data;
  },
};

// Alerts API
export const alertsApi = {
  getMyAlerts: async (filters?: AlertFilters): Promise<Alert[]> => {
    if (USE_MOCK) {
      await delay();
      let alerts = [...mockAlerts];
      if (filters?.status) {
        alerts = alerts.filter(a => a.status === filters.status);
      }
      if (filters?.limit) {
        alerts = alerts.slice(0, filters.limit);
      }
      return alerts;
    }
    const { data } = await apiClient.get<Alert[]>('/alerts/me', { params: filters });
    return data;
  },

  markAsRead: async (id: string): Promise<Alert> => {
    if (USE_MOCK) {
      await delay();
      const index = mockAlerts.findIndex(a => a.id === id);
      if (index !== -1) {
        mockAlerts[index] = {
          ...mockAlerts[index],
          status: 'read',
          read_at: new Date().toISOString(),
        };
        return mockAlerts[index];
      }
      throw new Error('Alert not found');
    }
    const { data } = await apiClient.post<Alert>(`/alerts/${id}/read`, {});
    return data;
  },
};

// Dashboard API
export const dashboardApi = {
  getStats: async (filters?: DashboardFilters): Promise<DashboardStats> => {
    if (USE_MOCK) {
      await delay();
      let expenses = mockExpenses.filter((e) => e.status === 'active');
      if (filters?.company_id) expenses = expenses.filter((e) => e.company_id === filters.company_id);
      if (filters?.department_id) expenses = expenses.filter((e) => e.department_id === filters.department_id);
      let validations = mockValidations.filter((v) => v.status === 'pending');
      if (filters?.month) {
        const monthStr = `${filters.month}-01`;
        validations = validations.filter((v) => v.validation_month === monthStr);
      }
      const alerts = mockAlerts.filter((a) => a.status === 'pending');
      const recurring = expenses.filter((e) => e.expense_type === 'recurring').length;
      const oneTime = expenses.filter((e) => e.expense_type === 'one_time').length;
      const totalValue = expenses.reduce((sum, e) => sum + (e.value_brl ?? e.value), 0);
      return {
        total_expenses_value: totalValue,
        monthly_expenses_value: totalValue * 0.3, // Mock
        average_expense_value: expenses.length > 0 ? totalValue / expenses.length : 0,
        pending_validations: validations.length,
        unread_alerts: alerts.length,
        active_expenses: expenses.length,
        recurring_expenses: recurring,
        one_time_expenses: oneTime,
        upcoming_renewals: expenses.filter((e) => e.renewal_date).length,
        cancelled_expenses_value: mockExpenses
          .filter((e) => e.status === 'cancelled')
          .reduce((sum, e) => sum + (e.value_brl ?? e.value), 0),
      };
    }
    const params = new URLSearchParams();
    if (filters?.company_id) params.append('company_id', filters.company_id);
    if (filters?.department_id) params.append('department_id', filters.department_id);
    if (filters?.month) params.append('month', filters.month);
    const { data } = await apiClient.get<DashboardStats>(`/dashboard/stats?${params.toString()}`);
    return data;
  },

  getExpensesByCategory: async (filters?: DashboardFilters, limit: number = 10): Promise<CategoryExpenseResponse> => {
    if (USE_MOCK) {
      await delay();
      return { items: [], total: 0 };
    }
    const params = new URLSearchParams();
    if (filters?.company_id) params.append('company_id', filters.company_id);
    if (filters?.department_id) params.append('department_id', filters.department_id);
    if (filters?.month) params.append('month', filters.month);
    params.append('limit', limit.toString());
    const { data } = await apiClient.get<CategoryExpenseResponse>(`/dashboard/expenses-by-category?${params.toString()}`);
    return data;
  },

  getExpensesByCompany: async (filters?: DashboardFilters, limit: number = 10): Promise<CompanyExpenseResponse> => {
    if (USE_MOCK) {
      await delay();
      return { items: [], total: 0 };
    }
    const params = new URLSearchParams();
    if (filters?.company_id) params.append('company_id', filters.company_id);
    if (filters?.department_id) params.append('department_id', filters.department_id);
    if (filters?.month) params.append('month', filters.month);
    params.append('limit', limit.toString());
    const { data } = await apiClient.get<CompanyExpenseResponse>(`/dashboard/expenses-by-company?${params.toString()}`);
    return data;
  },

  getExpensesByDepartment: async (filters?: DashboardFilters, limit: number = 10): Promise<DepartmentExpenseResponse> => {
    if (USE_MOCK) {
      await delay();
      return { items: [], total: 0 };
    }
    const params = new URLSearchParams();
    if (filters?.company_id) params.append('company_id', filters.company_id);
    if (filters?.department_id) params.append('department_id', filters.department_id);
    if (filters?.month) params.append('month', filters.month);
    params.append('limit', limit.toString());
    const { data } = await apiClient.get<DepartmentExpenseResponse>(`/dashboard/expenses-by-department?${params.toString()}`);
    return data;
  },

  getExpensesTimeline: async (filters?: DashboardFilters, months: number = 6): Promise<TimelineDataResponse> => {
    if (USE_MOCK) {
      await delay();
      return { data: [] };
    }
    const params = new URLSearchParams();
    if (filters?.company_id) params.append('company_id', filters.company_id);
    if (filters?.department_id) params.append('department_id', filters.department_id);
    if (filters?.month) params.append('month', filters.month);
    params.append('months', months.toString());
    const { data } = await apiClient.get<TimelineDataResponse>(`/dashboard/expenses-timeline?${params.toString()}`);
    return data;
  },

  getTopExpenses: async (filters?: DashboardFilters, limit: number = 10): Promise<TopExpenseResponse> => {
    if (USE_MOCK) {
      await delay();
      return { items: [] };
    }
    const params = new URLSearchParams();
    if (filters?.company_id) params.append('company_id', filters.company_id);
    if (filters?.department_id) params.append('department_id', filters.department_id);
    if (filters?.month) params.append('month', filters.month);
    params.append('limit', limit.toString());
    const { data } = await apiClient.get<TopExpenseResponse>(`/dashboard/top-expenses?${params.toString()}`);
    return data;
  },

  getExpensesByStatus: async (filters?: DashboardFilters): Promise<StatusDistributionResponse> => {
    if (USE_MOCK) {
      await delay();
      return { items: [], total_count: 0, total_value: 0 };
    }
    const params = new URLSearchParams();
    if (filters?.company_id) params.append('company_id', filters.company_id);
    if (filters?.department_id) params.append('department_id', filters.department_id);
    if (filters?.month) params.append('month', filters.month);
    const { data } = await apiClient.get<StatusDistributionResponse>(`/dashboard/expenses-by-status?${params.toString()}`);
    return data;
  },

  getUpcomingRenewals: async (filters?: DashboardFilters, days: number = 30, limit: number = 10): Promise<UpcomingRenewalsResponse> => {
    if (USE_MOCK) {
      await delay();
      return { items: [], count: 0 };
    }
    const params = new URLSearchParams();
    if (filters?.company_id) params.append('company_id', filters.company_id);
    if (filters?.department_id) params.append('department_id', filters.department_id);
    params.append('days', days.toString());
    params.append('limit', limit.toString());
    const { data } = await apiClient.get<UpcomingRenewalsResponse>(`/dashboard/upcoming-renewals?${params.toString()}`);
    return data;
  },

  getRecentExpenses: async (limit: number = 5, filters?: DashboardFilters): Promise<Expense[]> => {
    if (USE_MOCK) {
      await delay();
      let list = [...mockExpenses];
      if (filters?.company_id) list = list.filter((e) => e.company_id === filters.company_id);
      if (filters?.department_id) list = list.filter((e) => e.department_id === filters.department_id);
      return list.slice(0, limit);
    }
    const expenseFilters: ExpenseFilters = {};
    if (filters?.company_id) expenseFilters.company_ids = [filters.company_id];
    if (filters?.department_id) expenseFilters.department_ids = [filters.department_id];
    const expenses = await expensesApi.getAll(expenseFilters);
    let filteredByMonth = expenses;
    if (filters?.month) {
      const [yearStr, monthStr] = filters.month.split('-');
      const year = Number(yearStr);
      const month = Number(monthStr);
      if (!Number.isNaN(year) && !Number.isNaN(month)) {
        filteredByMonth = expenses.filter((expense) => {
          if (!expense.created_at) return false;
          const createdAt = new Date(expense.created_at);
          return createdAt.getFullYear() === year && createdAt.getMonth() + 1 === month;
        });
      }
    }
    return filteredByMonth.slice(0, limit);
  },

  getRecentAlerts: async (limit: number = 5): Promise<Alert[]> => {
    if (USE_MOCK) {
      await delay();
      return mockAlerts.slice(0, limit);
    }
    return alertsApi.getMyAlerts({ limit });
  },
};
