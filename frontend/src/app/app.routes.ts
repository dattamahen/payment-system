import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  {
    path: 'login',
    loadComponent: () => import('./features/tenant-admin/login/login.page').then(m => m.LoginPage),
  },
  {
    path: 'super-admin',
    canActivate: [authGuard, roleGuard('super_admin')],
    children: [
      {
        path: 'tenants',
        loadComponent: () => import('./features/super-admin/tenants/tenants.page').then(m => m.TenantsPage),
      },
      {
        path: 'tenants/create',
        loadComponent: () => import('./features/super-admin/tenants/create-tenant.page').then(m => m.CreateTenantPage),
      },
    ],
  },
  {
    path: 'dashboard',
    canActivate: [authGuard],
    children: [
      {
        path: 'events',
        loadComponent: () => import('./features/events/events.page').then(m => m.EventsPage),
      },
      {
        path: 'events/create',
        loadComponent: () => import('./features/events/create-event.page').then(m => m.CreateEventPage),
      },
      {
        path: 'events/:id',
        loadComponent: () => import('./features/events/event-detail/event-detail.page').then(m => m.EventDetailPage),
      },
      {
        path: 'forms',
        loadComponent: () => import('./features/forms/forms.page').then(m => m.FormsPage),
      },
      {
        path: 'forms/builder',
        loadComponent: () => import('./features/forms/form-builder/form-builder.page').then(m => m.FormBuilderPage),
      },
      {
        path: 'registrations',
        loadComponent: () => import('./features/registrations/registrations.page').then(m => m.RegistrationsPage),
      },
      {
        path: 'payments',
        loadComponent: () => import('./features/payments/payments.page').then(m => m.PaymentsPage),
      },
      {
        path: 'analytics',
        loadComponent: () => import('./features/analytics/analytics.page').then(m => m.AnalyticsPage),
      },
    ],
  },
];
