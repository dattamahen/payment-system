import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { IonContent, IonHeader, IonTitle, IonToolbar, IonButton, IonCard, IonCardContent, IonCardHeader, IonCardTitle, IonItem, IonInput, IonTextarea, IonButtons } from '@ionic/angular/standalone';
import { ApiService } from '../../../core/services/api.service';

@Component({
  selector: 'app-create-tenant',
  standalone: true,
  imports: [CommonModule, FormsModule, IonContent, IonHeader, IonTitle, IonToolbar, IonButton, IonCard, IonCardContent, IonCardHeader, IonCardTitle, IonItem, IonInput, IonTextarea, IonButtons],
  templateUrl: './create-tenant.page.html',
  styleUrls: ['./create-tenant.page.scss'],
})
export class CreateTenantPage {
  tenant: any = {
    name: '', slug: '', owner_email: '', owner_password: '', plan: 'free',
    config: {
      razorpay_key_id: '',
      razorpay_key_secret: '',
      whatsapp_number: '',
      whatsapp_phone_number_id: '',
      whatsapp_api_key: '',
      google_sheets_credentials: '',
    }
  };
  msg = '';
  err = false;

  constructor(private api: ApiService, private router: Router) {}

  goBack() { this.router.navigate(['/super-admin/tenants']); }

  create() {
    this.msg = '';
    this.err = false;
    // Remove empty config fields
    const payload = { ...this.tenant };
    const config: any = {};
    if (payload.config.razorpay_key_id) config.razorpay_key_id = payload.config.razorpay_key_id;
    if (payload.config.razorpay_key_secret) config.razorpay_key_secret = payload.config.razorpay_key_secret;
    if (payload.config.whatsapp_number) config.whatsapp_number = payload.config.whatsapp_number;
    if (payload.config.whatsapp_phone_number_id) config.whatsapp_phone_number_id = payload.config.whatsapp_phone_number_id;
    if (payload.config.whatsapp_api_key) config.whatsapp_api_key = payload.config.whatsapp_api_key;
    if (payload.config.google_sheets_credentials) config.google_sheets_credentials = payload.config.google_sheets_credentials;
    payload.config = Object.keys(config).length ? config : undefined;

    this.api.createTenant(payload).subscribe({
      next: () => { this.msg = 'Tenant created!'; setTimeout(() => this.router.navigate(['/super-admin/tenants']), 1000); },
      error: (e) => { this.msg = e.error?.detail || 'Failed to create tenant'; this.err = true; }
    });
  }
}
