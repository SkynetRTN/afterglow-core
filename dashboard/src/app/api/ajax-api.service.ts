import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Oauth2Client } from './models/oauth2-client';
import { Oauth2Provider } from './models/oauth2-provider';

export interface AjaxResponse<Type> {
  data: Type;
}

export interface AjaxErrorResponse extends HttpErrorResponse {
  error: AjaxError
}

export interface AjaxError {
  error: {
    detail: string,
    id: string,
    meta: {
      error_msg: string
    }
  }
}


@Injectable({
  providedIn: 'root',
})
export class AjaxApiService {
  constructor(private http: HttpClient) { }


  login(credentials: { username: string, password: string }) {
    return this.http.post('ajax/auth/sign-in', credentials)
  }

  signInWithOauthCode(credentials: {
    pluginId: string;
    code: string;
    next: string;
    redirectUri: string;
  }) {

    let params = new HttpParams()
      .set("code", credentials.code)
      .set("redirect_uri", credentials.redirectUri);

    return this.http.get(`ajax/oauth2/providers/${credentials.pluginId}/authorized`, { params: params })
  }

  getOauth2Providers() {
    return this.http.get<AjaxResponse<Oauth2Provider[]>>('ajax/oauth2/providers')
  }

  getOauth2Clients() {
    return this.http.get<AjaxResponse<Oauth2Client[]>>('ajax/oauth2/clients')
  }

}
