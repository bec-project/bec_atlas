import { Component } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatIcon } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatInputModule } from '@angular/material/input';
import {
  UntypedFormBuilder,
  UntypedFormGroup,
  Validators,
} from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../core/auth.service';
import { ActivatedRoute, Router } from '@angular/router';
import { AppConfig, AppConfigService } from '../app-config.service';
import { HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login',
  imports: [
    CommonModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatTabsModule,
    MatTooltipModule,
    MatIcon,
    ReactiveFormsModule,
  ],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  hide = true;
  form: UntypedFormGroup;
  loginMessage = ' ';
  appConfig!: AppConfig;
  backgroundImage!: string;
  images: string[] = [
    'assets/backgrounds/psi_background_north.jpg',
    'assets/backgrounds/psi_background_south.jpg',
    'assets/backgrounds/psi_sdsc.jpg',
    'assets/backgrounds/psi_cable.jpg',
  ];

  constructor(
    private appConfigService: AppConfigService,
    private fb: UntypedFormBuilder,
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    this.appConfig = this.appConfigService.getConfig();
    this.form = this.fb.group({
      email: ['', Validators.required],
      password: ['', Validators.required],
    });
  }

  ngOnInit(): void {
    // select a random background image
    this.backgroundImage =
      this.images[Math.floor(Math.random() * this.images.length)];

    if (this.authService.forceReload) {
      window.location.reload();
    }
  }

  async login() {
    const val = this.form.value;
    if (val.email && val.password) {
      try {
        const data = await firstValueFrom(
          this.authService.login(val.email, val.password)
        );
        console.log('User is logged in');
        this.router.navigateByUrl('/overview-grid');
      } catch (error: unknown) {
        switch ((error as HttpErrorResponse).statusText) {
          case 'Unknown Error':
            this.loginMessage = 'Authentication failed.';
            return;
          case 'Unauthorized':
            this.loginMessage =
              'User name / email or password are not correct.';
            return;
          default:
            this.loginMessage = 'Authentication failed.';
            return;
        }
      }
    }
  }
}
