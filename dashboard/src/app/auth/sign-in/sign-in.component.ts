// @ts-ignore

import { Component, NgZone, OnInit, ViewChild, ViewEncapsulation } from '@angular/core';
import { Location } from '@angular/common';
import { FormBuilder, FormGroup, NgForm, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router'
import { BehaviorSubject, combineLatest, map, take } from 'rxjs';
import { AjaxApiService } from 'src/app/api/ajax-api.service';
import { Oauth2Client } from 'src/app/api/models/oauth2-client';
import { Oauth2Provider } from 'src/app/api/models/oauth2-provider';
import { AuthService } from '../auth.service';
// import { FuseAlertType } from '@fuse/components/alert';

@Component({
    selector: 'auth-sign-in',
    templateUrl: './sign-in.component.html',
    encapsulation: ViewEncapsulation.None,
})
export class AuthSignInComponent implements OnInit {
    @ViewChild('signInNgForm') signInNgForm: NgForm;

    // alert: { type: FuseAlertType; message: string } = {
    //     type: 'success',
    //     message: '',
    // };
    signInForm: FormGroup;
    showAlert: boolean = false;



    providersLoading$ = new BehaviorSubject<boolean>(false);
    providers$ = new BehaviorSubject<Oauth2Provider[]>([])

    clientsLoading$ = new BehaviorSubject<boolean>(false);
    clients$ = new BehaviorSubject<Oauth2Client[]>([])
    next$ = combineLatest(this.clients$, this._activatedRoute.queryParams).pipe(
        map(([clients, queryParams]) => {
            let clientId = queryParams['client_id'];
            let redirectUri = queryParams['redirect_uri'];
            if (!redirectUri || !clientId) return null;

            let client = clients.find(client => client.id == clientId && client.redirect_uris.includes(redirectUri))
            if (!client) return null;
            return redirectUri;
        })
    )


    /**
     * Constructor
     */
    constructor(
        private _activatedRoute: ActivatedRoute,
        private _authService: AuthService,
        private _ajaxApiService: AjaxApiService,
        private _formBuilder: FormBuilder,
        private _router: Router,
        private _zone: NgZone,
        private _location: Location,
    ) {



    }
    private signInNext(): any {
        // Set the redirect url.
        // The '/signed-in-redirect' is a dummy url to catch the request and redirect the user
        // to the correct page after a successful sign in. This way, that url can be set via
        // routing file and we don't have to touch here.
        const redirectURL = this._activatedRoute.snapshot.queryParamMap.get('redirectURL') || '/signed-in-redirect';

        // Navigate to the redirect url
        this._zone.run(
            () => {
                this._router.navigateByUrl(redirectURL);
            }
        );
    }

    private signInError(response: Response): any {
        // Re-enable the form
        this.signInForm.enable();

        // Reset the form
        this.signInNgForm.resetForm();
        // Set the alert
        let message: string = 'Wrong username or password';
        if (response.status === 428 || response.status === 401) {
            // message = response.error['message'];
        }
        // this.alert = {
        //     type: 'error',
        //     message: message
        // };

        // Show the alert
        this.showAlert = true;
    }
    // -----------------------------------------------------------------------------------------------------
    // @ Lifecycle hooks
    // -----------------------------------------------------------------------------------------------------

    /**
     * On init
     */
    ngOnInit(): void {
        // Create the form
        this.signInForm = this._formBuilder.group({
            username: ['', [Validators.required]],
            password: ['', Validators.required],
            rememberMe: [''],
        });

        this.providersLoading$.next(true);
        this._ajaxApiService.getOauth2Providers().pipe(
            take(1),
        ).subscribe({
            next: (response) => {
                this.providers$.next(response.data);
            },
            error: (error) => {
                this.providers$.next([]);
            },
            complete: () => { this.providersLoading$.next(false) }
        })

        this.clientsLoading$.next(true);
        this._ajaxApiService.getOauth2Clients().pipe(
            take(1),
        ).subscribe({
            next: (response) => {
                this.clients$.next(response.data);
            },
            error: (error) => {
                this.clients$.next([]);
            },
            complete: () => { this.clientsLoading$.next(false) }
        })

        // google.accounts.id.initialize({
        //     client_id: '378564412993-h9sjps04r0pdvppr8er2f6hk6maojn7r.apps.googleusercontent.com',
        //     prompt_parent_id: 'googleSignIn',
        //     callback: (response) => {
        //         this._authService.signInWithGoogle(response).subscribe(() => {this.signInNext(); }, (httpResponse) => {this.signInError(httpResponse); });
        //     }
        // });

        // google.accounts.id.renderButton(
        //     document.getElementById('googleSignIn'),
        //     {
        //         type: 'standard',
        //         size: 'large',
        //         shape: 'pill',
        //         logo_alignment: 'left',
        //         text: 'continue_with',
        //         width: '320'
        //     }
        // );
    }

    // -----------------------------------------------------------------------------------------------------
    // @ Public methods
    // -----------------------------------------------------------------------------------------------------

    /**
     * Sign in
     */
    signIn(): void {
        // Return if the form is invalid
        if (this.signInForm.invalid) {
            return;
        }

        // Disable the form
        this.signInForm.disable();

        // Hide the alert
        this.showAlert = false;

        // Sign in
        // this._authService.signIn(this.signInForm.value).subscribe(() => { this.signInNext(); }, (response) => { this.signInError(response); });
    }

    getAuthorizeUrl(plugin: Oauth2Provider, next: string) {
        let state = {
            plugin: plugin.id,
            next: next
        };

        let redirectUri = this._location.prepareExternalUrl('/oauth2/authorized');

        let params = new URLSearchParams();
        params.append("response_type", "code");
        params.append("state", JSON.stringify(state));
        params.append("client_id", plugin.client_id);
        params.append("redirect_uri", redirectUri);

        return `${plugin.authorize_url}?${params.toString()}`;
    }
}
