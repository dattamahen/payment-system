import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { IonContent, IonHeader, IonTitle, IonToolbar, IonButton, IonCard, IonCardContent, IonCardHeader, IonCardTitle, IonItem, IonInput, IonSelect, IonSelectOption, IonTextarea, IonButtons } from '@ionic/angular/standalone';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-create-event',
  standalone: true,
  imports: [CommonModule, FormsModule, IonContent, IonHeader, IonTitle, IonToolbar, IonButton, IonCard, IonCardContent, IonCardHeader, IonCardTitle, IonItem, IonInput, IonSelect, IonSelectOption, IonTextarea, IonButtons],
  templateUrl: './create-event.page.html',
  styleUrls: ['./create-event.page.scss'],
})
export class CreateEventPage {
  msg = '';
  err = false;
  event: any = {
    name: '', slug: '', description: '', event_date: '', registration_deadline: '',
    max_participants: 500,
    venue: { name: '', address: '', city: '', map_url: '' },
    pricing: { type: 'free', amount: null, currency: 'INR' },
    form_fields: [
      { label: 'Full Name', type: 'text', required: true, optionsStr: '' },
      { label: 'Email', type: 'email', required: true, optionsStr: '' },
      { label: 'Phone', type: 'phone', required: true, optionsStr: '' },
    ]
  };

  constructor(private api: ApiService, private router: Router) {}

  goBack() { this.router.navigate(['/dashboard/events']); }

  addField() { this.event.form_fields.push({ label: '', type: 'text', required: true, optionsStr: '' }); }

  removeField(i: number) { this.event.form_fields.splice(i, 1); }

  createEvent() {
    this.msg = '';
    this.err = false;
    const payload = {
      ...this.event,
      form_fields: this.event.form_fields.map((f: any) => ({
        label: f.label, type: f.type, required: f.required,
        options: f.type === 'select' && f.optionsStr ? f.optionsStr.split(',').map((o: string) => o.trim()) : null
      }))
    };
    this.api.createEvent(payload).subscribe({
      next: () => { this.msg = 'Event created!'; setTimeout(() => this.router.navigate(['/dashboard/events']), 1000); },
      error: (e) => { this.msg = e.error?.detail || 'Failed to create event'; this.err = true; }
    });
  }
}
