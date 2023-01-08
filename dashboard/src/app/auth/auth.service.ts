import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, throwError } from 'rxjs';
import { switchMap, tap } from 'rxjs/operators';
import { AjaxApiService } from '../api/ajax-api.service';
import { CookieService } from 'ngx-cookie';

@Injectable()
export class AuthService {
  private _authenticated: boolean = false;

  /**
   * Constructor
   */
  constructor(
    private ajaxApiService: AjaxApiService,
    private httpClient: HttpClient,
    private cookieService: CookieService
  ) { }

  // -----------------------------------------------------------------------------------------------------
  // @ Accessors
  // -----------------------------------------------------------------------------------------------------

  /**
   * Setter & getter for access token
   */

  get userId() {
    return this.cookieService.get('afterglow_core_user_id')
  }

  get token() {
    return this.cookieService.get('afterglow_core_access_token')
  }

  // -----------------------------------------------------------------------------------------------------
  // @ Public methods
  // -----------------------------------------------------------------------------------------------------


}
