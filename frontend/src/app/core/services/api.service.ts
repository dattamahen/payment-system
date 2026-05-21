import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Tenants
  getTenants() { return this.http.get<any[]>(`${this.base}/admin/tenants`); }
  createTenant(data: any) { return this.http.post(`${this.base}/admin/tenants/`, data); }
  createTenantUser(tenantId: string, data: any) { return this.http.post(`${this.base}/admin/tenants/${tenantId}/users`, data); }
  getTenantEvents(tenantId: string) { return this.http.get<any[]>(`${this.base}/admin/tenants/${tenantId}/events`); }
  getTenantEventDetail(tenantId: string, eventId: string) { return this.http.get<any>(`${this.base}/admin/tenants/${tenantId}/events/${eventId}`); }
  changeTenantEventStatus(tenantId: string, eventId: string, status: string) { return this.http.patch(`${this.base}/admin/tenants/${tenantId}/events/${eventId}/status?status=${status}`, {}); }
  updateTenant(id: string, data: any) { return this.http.patch(`${this.base}/admin/tenants/${id}`, data); }

  // Events
  getEvents() { return this.http.get<any[]>(`${this.base}/events`); }
  getEvent(id: string) { return this.http.get<any>(`${this.base}/events/${id}`); }
  createEvent(data: any) { return this.http.post(`${this.base}/events`, data); }
  updateEvent(id: string, data: any) { return this.http.patch(`${this.base}/events/${id}`, data); }
  changeEventStatus(id: string, status: string) { return this.http.patch(`${this.base}/events/${id}/status?status=${status}`, {}); }
  getEventRegistrations(eventId: string) { return this.http.get<any[]>(`${this.base}/events/${eventId}/registrations`); }
  generateQR(eventId: string) { return this.http.post(`${this.base}/events/${eventId}/generate-qr`, {}); }

  // Forms
  getForms() { return this.http.get<any[]>(`${this.base}/forms`); }
  getForm(id: string) { return this.http.get<any>(`${this.base}/forms/${id}`); }
  createForm(data: any) { return this.http.post(`${this.base}/forms`, data); }
  updateForm(id: string, data: any) { return this.http.patch(`${this.base}/forms/${id}`, data); }

  // Registrations
  getRegistrations(eventId?: string) {
    const params = eventId ? `?event_id=${eventId}` : '';
    return this.http.get<any[]>(`${this.base}/registrations${params}`);
  }

  // Payments
  getPaymentStatus(registrationId: string) { return this.http.get(`${this.base}/payments/${registrationId}`); }

  // Sheets
  syncSheets(eventId: string) { return this.http.post(`${this.base}/sheets/${eventId}/sync`, {}); }
  getSheetMapping(eventId: string) { return this.http.get(`${this.base}/sheets/${eventId}/mapping`); }
  updateSheetMapping(eventId: string, mapping: any) { return this.http.patch(`${this.base}/sheets/${eventId}/mapping`, mapping); }
}
