import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { IonContent, IonHeader, IonToolbar, IonItem, IonInput, IonButton, IonCard, IonCardContent, IonCardHeader, IonCardTitle } from '@ionic/angular/standalone';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, IonContent, IonHeader, IonToolbar, IonItem, IonInput, IonButton, IonCard, IonCardContent, IonCardHeader, IonCardTitle],
  templateUrl: './login.page.html',
  styleUrls: ['./login.page.scss'],
})
export class LoginPage implements OnInit {
  email = '';
  password = '';
  error = '';

  constructor(private auth: AuthService, private router: Router) {}

  ngOnInit() {
    this.email = '';
    this.password = '';
    this.error = '';
  }

  login() {
    this.auth.login(this.email, this.password).subscribe({
      next: () => {
        const role = this.auth.getRole();
        if (role === 'super_admin') {
          this.router.navigate(['/super-admin/tenants']);
        } else {
          this.router.navigate(['/dashboard/events']);
        }
      },
      error: (err) => this.error = err.error?.detail || 'Login failed',
    });
  }
}
