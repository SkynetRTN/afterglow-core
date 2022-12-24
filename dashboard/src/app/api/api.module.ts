import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AjaxApiService } from './ajax-api.service';
import { HttpClientModule } from '@angular/common/http';



@NgModule({
  declarations: [],
  imports: [
    CommonModule,
    HttpClientModule,
  ],
  providers: [
    AjaxApiService,
  ]
})
export class ApiModule { }
