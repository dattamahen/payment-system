import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { IonContent, IonHeader, IonTitle, IonToolbar, IonButton, IonCard, IonCardContent, IonCardHeader, IonCardTitle, IonItem, IonInput, IonLabel, IonList, IonSelect, IonSelectOption, IonBadge, IonButtons } from '@ionic/angular/standalone';
import { ViewWillEnter } from '@ionic/angular/standalone';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-tenants',
  standalone: true,
  imports: [CommonModule, FormsModule, IonContent, IonHeader, IonTitle, IonToolbar, IonButton, IonCard, IonCardContent, IonCardHeader, IonCardTitle, IonItem, IonInput, IonLabel, IonList, IonSelect, IonSelectOption, IonBadge, IonButtons],
  templateUrl: './tenants.page.html',
  styleUrls: ['./tenants.page.scss'],
})
export class TenantsPage implements OnInit, ViewWillEnter {
  view: 'list' | 'events' | 'event-detail' | 'edit' = 'list';
  tenants: any[] = [];
  selectedTenant: any = null;
  selectedTenantForUser: any = null;
  tenantEvents: any[] = [];
  eventDetail: any = null;
  newUser = { name: '', email: '', password: '', role: 'tenant_admin' };
  userMsg = '';
  editTenant: any = null;
  editMsg = '';
  editErr = false;

  constructor(private api: ApiService, private auth: AuthService, private router: Router) {}

  ngOnInit() { this.loadTenants(); }

  ionViewWillEnter() { this.loadTenants(); }

  getTitle(): string {
    if (this.view === 'edit') return 'Edit Tenant: ' + (this.editTenant?.name || '');
    if (this.view === 'event-detail') return this.eventDetail?.name || 'Event Detail';
    if (this.view === 'events') return this.selectedTenant?.name + ' - Events';
    return 'Tenants';
  }

  goBack() {
    if (this.view === 'edit') { this.view = 'list'; this.editTenant = null; this.editMsg = ''; }
    else if (this.view === 'event-detail') { this.view = 'events'; this.eventDetail = null; }
    else if (this.view === 'events') { this.view = 'list'; this.tenantEvents = []; }
  }

  goToCreate() { this.router.navigate(['/super-admin/tenants/create']); }

  logout() { this.auth.logout(); this.router.navigate(['/login']); }

  loadTenants() { this.api.getTenants().subscribe(t => this.tenants = t); }

  selectTenantForUser(t: any) { this.selectedTenantForUser = t; this.userMsg = ''; }

  createUser() {
    this.api.createTenantUser(this.selectedTenantForUser.id, this.newUser).subscribe({
      next: () => { this.userMsg = 'User created!'; this.newUser = { name: '', email: '', password: '', role: 'tenant_admin' }; },
      error: (err) => this.userMsg = err.error?.detail || 'Failed',
    });
  }

  viewTenantEvents(t: any) {
    this.selectedTenant = t;
    this.api.getTenantEvents(t.id).subscribe(events => { this.tenantEvents = events; this.view = 'events'; });
  }

  openEditTenant(t: any) {
    this.editTenant = { ...t, config: { whatsapp_number: '', whatsapp_phone_number_id: '', whatsapp_api_key: '', razorpay_key_id: '', razorpay_key_secret: '' } };
    this.editMsg = '';
    this.editErr = false;
    this.view = 'edit';
  }

  saveEditTenant() {
    const payload: any = { name: this.editTenant.name };
    const config: any = {};
    if (this.editTenant.config.whatsapp_number) config.whatsapp_number = this.editTenant.config.whatsapp_number;
    if (this.editTenant.config.whatsapp_phone_number_id) config.whatsapp_phone_number_id = this.editTenant.config.whatsapp_phone_number_id;
    if (this.editTenant.config.whatsapp_api_key) config.whatsapp_api_key = this.editTenant.config.whatsapp_api_key;
    if (this.editTenant.config.razorpay_key_id) config.razorpay_key_id = this.editTenant.config.razorpay_key_id;
    if (this.editTenant.config.razorpay_key_secret) config.razorpay_key_secret = this.editTenant.config.razorpay_key_secret;
    if (Object.keys(config).length) payload.config = config;
    this.api.updateTenant(this.editTenant.id, payload).subscribe({
      next: () => { this.editMsg = 'Tenant updated!'; this.editErr = false; this.loadTenants(); },
      error: (e) => { this.editMsg = e.error?.detail || 'Failed'; this.editErr = true; }
    });
  }

  activateTenant(t: any) {
    this.api.updateTenant(t.id, { status: 'active' }).subscribe(() => this.loadTenants());
  }

  deactivateTenant(t: any) {
    this.api.updateTenant(t.id, { status: 'inactive' }).subscribe(() => this.loadTenants());
  }

  getEventStatusColor(status: string): string {
    switch (status) {
      case 'active': return 'success';
      case 'paused': return 'warning';
      case 'stopped': return 'danger';
      default: return 'medium';
    }
  }

  changeEventStatus(eventId: string, status: string) {
    this.api.changeTenantEventStatus(this.selectedTenant.id, eventId, status).subscribe({
      next: () => this.api.getTenantEvents(this.selectedTenant.id).subscribe(events => this.tenantEvents = events)
    });
  }

  viewEventDetail(e: any) {
    this.api.getTenantEventDetail(this.selectedTenant.id, e.id).subscribe(detail => { this.eventDetail = detail; this.view = 'event-detail'; });
  }

  formatResponses(responses: any): string {
    if (!responses) return '-';
    return Object.entries(responses).map(([k, v]) => `${k}: ${v}`).join(' | ');
  }

  downloadExcel() {
    if (!this.eventDetail) return;
    this.api.downloadExcel(this.eventDetail.id).subscribe((blob: any) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${this.eventDetail.name}_registrations.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    });
  }
}
