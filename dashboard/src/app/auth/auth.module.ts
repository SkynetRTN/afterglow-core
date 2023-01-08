import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthSignInComponent } from './sign-in/sign-in.component';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';
import { ReactiveFormsModule } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { AuthService } from './auth.service';
import { HttpClientModule } from '@angular/common/http';
import { AuthComponent } from './auth.component';
import { authRoutes } from './auth.routing';
import { OauthAuthorizedComponent } from './oauth-authorized/oauth-authorized.component';


@NgModule({
  declarations: [AuthSignInComponent, AuthComponent, OauthAuthorizedComponent],
  imports: [
    RouterModule.forChild(authRoutes),
    CommonModule,
    MatFormFieldModule,
    MatProgressSpinnerModule,
    MatButtonModule,
    MatCheckboxModule,
    MatInputModule,
    MatIconModule,
    ReactiveFormsModule,
    HttpClientModule
  ],
  providers: [
    AuthService
  ]
})
export class AuthModule { }
