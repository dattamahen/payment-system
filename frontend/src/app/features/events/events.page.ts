import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { IonContent, IonHeader, IonTitle, IonToolbar, IonButton, IonBadge, IonButtons } from '@ionic/angular/standalone';
import { ViewWillEnter } from '@ionic/angular/standalone';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-events',
  standalone: true,
  imports: [CommonModule, IonContent, IonHeader, IonTitle, IonToolbar, IonButton, IonBadge, IonButtons],
  templateUrl: './events.page.html',
  styleUrls: ['./events.page.scss'],
})
export class EventsPage implements OnInit, ViewWillEnter {
  events: any[] = [];
  selectedEvent: any = null;
  registrations: any[] = [];

  constructor(private api: ApiService, private auth: AuthService, private router: Router) {}

  ngOnInit() { this.loadEvents(); }

  ionViewWillEnter() { this.loadEvents(); }

  loadEvents() {
    this.api.getEvents().subscribe({ next: (e) => this.events = e, error: () => {} });
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'active': return 'success';
      case 'paused': return 'warning';
      case 'stopped': return 'danger';
      default: return 'medium';
    }
  }

  changeStatus(eventId: string, status: string) {
    this.api.changeEventStatus(eventId, status).subscribe({ next: () => this.loadEvents() });
  }

  viewRegistrations(event: any) {
    this.selectedEvent = event;
    this.api.getEventRegistrations(event.id).subscribe({
      next: (regs) => this.registrations = regs,
      error: () => this.registrations = []
    });
  }

  downloadPdf() {
    const token = this.auth.getToken();
    const url = `/api/v1/events/${this.selectedEvent.id}/registrations/download?token=${token}`;
    window.open(url, '_blank');
  }

  downloadExcel() {
    if (!this.selectedEvent) return;
    this.api.downloadExcel(this.selectedEvent.id).subscribe((blob: any) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${this.selectedEvent.name}_registrations.xlsx`;
      a.click();
      window.URL.revokeObjectURL(url);
    });
  }

  goToCreate() { this.router.navigate(['/dashboard/events/create']); }

  logout() { this.auth.logout(); this.router.navigate(['/login']); }
}
