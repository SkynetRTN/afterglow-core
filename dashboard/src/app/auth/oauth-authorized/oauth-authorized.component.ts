import { AfterViewInit, Component, OnInit, ViewEncapsulation } from '@angular/core';
import { Location } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { AjaxApiService, AjaxErrorResponse, AjaxResponse } from 'src/app/api/ajax-api.service';
import { AuthService } from '../auth.service';

@Component({
  selector: 'app-oauth-authorized',
  templateUrl: './oauth-authorized.component.html',
  styleUrls: ['./oauth-authorized.component.scss'],
  encapsulation: ViewEncapsulation.None
})
export class OauthAuthorizedComponent implements OnInit, AfterViewInit {
  error = '';

  constructor(private activatedRoute: ActivatedRoute, private ajaxApiService: AjaxApiService, private authService: AuthService, private location: Location) { }

  ngOnInit(): void {


  }

  ngAfterViewInit() {
    let code = this.activatedRoute.snapshot.queryParams['code']
    if (!code || typeof code != "string") {
      this.error = "Authorization code is required";
      return;
    }
    let state = this.activatedRoute.snapshot.queryParams['state']
    if (!state || typeof state != "string") {
      this.error = "Invalid state";
      return;
    }

    let stateObj = JSON.parse(state) as { plugin: string; next: string };
    if (!stateObj) {
      this.error = "Invalid state";
      return;
    }

    if (!stateObj.plugin) {
      this.error = "Plugin ID is required";
      return;
    }

    let next = stateObj.next;
    let pluginId = stateObj.plugin;
    let redirectUri = window.location.origin + this.location.prepareExternalUrl('/oauth2/authorized')

    this.ajaxApiService.signInWithOauthCode({ pluginId, code, next, redirectUri }).subscribe({
      next: () => {
        if (this.authService.userId && this.authService.token) {
          window.location.href = next || window.location.origin;
        }
        else {
          this.error = 'Unexpected error occurred.  Login was successful, but token was not received'
        }
      },
      error: (resp: AjaxErrorResponse) => {
        this.error = resp.error?.error?.meta?.error_msg || 'An unexpected error occurred'
      },
      complete: () => { }
    });
  }
}
