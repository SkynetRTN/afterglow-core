import { Route } from '@angular/router';
import { AuthComponent } from './auth.component';
import { OauthAuthorizedComponent } from './oauth-authorized/oauth-authorized.component';
import { AuthSignInComponent } from './sign-in/sign-in.component';

export const authRoutes: Route[] = [
  {
    path: '',
    component: AuthComponent,
    children: [
      {
        path: '',
        redirectTo: 'sign-in',
        pathMatch: 'full',
      },
      {
        path: 'sign-in',
        component: AuthSignInComponent
      },
      {
        path: 'oauth2/authorized',
        component: OauthAuthorizedComponent
      },
    ]
  },
];
