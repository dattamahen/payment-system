import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { IonContent, IonHeader, IonTitle, IonToolbar, IonButton, IonCard, IonCardContent, IonCardHeader, IonCardTitle, IonItem, IonInput, IonLabel, IonList, IonSelect, IonSelectOption, IonBadge, IonButtons } from '@ionic/angular/standalone';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-tenants',
  standalone: true,
  imports: [CommonModule, FormsModule, IonContent, IonHeader, IonTitle, IonToolbar, IonButton, IonCard, IonCardContent, IonCardHeader, IonCardTitle, IonItem, IonInput, IonLabel, IonList, IonSelect, IonSelectOption, IonBadge, IonButtons],
  templateUrl: './tenants.page.html',
  styleUrls: ['./tenants.page.scss'],
})
export class TenantsPage implements OnInit {
  view: 'list' | 'events' | 'event-detail' = 'list';
  tenants: any[] = [];
  selectedTenant: any = null;
  selectedTenantForUser: any = null;
  tenantEvents: any[] = [];
  eventDetail: any = null;
  newUser = { name: '', email: '', password: '', role: 'tenant_admin' };
  userMsg = '';

  constructor(private api: ApiService, private auth: AuthService, private router: Router) {}

  ngOnInit() { this.loadTenants(); }

  getTitle(): string {
    if (this.view === 'event-detail') return this.eventDetail?.name || 'Event Detail';
    if (this.view === 'events') return this.selectedTenant?.name + ' - Events';
    return 'Tenants';
  }

  goBack() {
    if (this.view === 'event-detail') { this.view = 'events'; this.eventDetail = null; }
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
}
