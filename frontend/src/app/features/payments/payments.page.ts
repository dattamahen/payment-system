import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonContent, IonHeader, IonTitle, IonToolbar, IonList, IonItem, IonLabel, IonBadge, IonSpinner, IonNote } from '@ionic/angular/standalone';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-payments',
  standalone: true,
  imports: [CommonModule, IonContent, IonHeader, IonTitle, IonToolbar, IonList, IonItem, IonLabel, IonBadge, IonSpinner, IonNote],
  template: `
    <ion-header>
      <ion-toolbar color="primary">
        <ion-title>Payments</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content class="ion-padding">
      <ion-spinner *ngIf="loading"></ion-spinner>
      <p *ngIf="!loading && !registrations.length">No payments found.</p>
      <ion-list *ngIf="!loading && registrations.length">
        <ion-item *ngFor="let r of registrations">
          <ion-label>
            <h2>{{ r.phone }}</h2>
            <p>₹{{ r.payment?.amount || 0 }} &middot; {{ r.payment?.short_url ? 'Link sent' : '' }}</p>
            <ion-note>{{ r.created_at | date:'short' }}</ion-note>
          </ion-label>
          <ion-badge slot="end" [color]="statusColor(r.payment?.status)">
            {{ r.payment?.status || 'N/A' }}
          </ion-badge>
        </ion-item>
      </ion-list>
    </ion-content>
  `,
})
export class PaymentsPage implements OnInit {
  registrations: any[] = [];
  loading = true;

  constructor(private api: ApiService) {}

  ngOnInit() {
    this.api.getRegistrations().subscribe({
      next: (data) => {
        this.registrations = data.filter((r: any) => r.payment && r.payment.status);
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  statusColor(status: string): string {
    if (status === 'paid') return 'success';
    if (status === 'link_sent') return 'warning';
    return 'medium';
  }
}
