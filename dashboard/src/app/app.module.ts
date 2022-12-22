import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';

import { CookieModule } from 'ngx-cookie';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { AuthModule } from './auth/auth.module';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

@NgModule({
  declarations: [
    AppComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    AuthModule,
    BrowserAnimationsModule,
    CookieModule.withOptions()
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
