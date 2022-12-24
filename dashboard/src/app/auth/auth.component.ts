import { Component, OnInit, ViewEncapsulation } from '@angular/core';

@Component({
  selector: 'app-auth',
  templateUrl: './auth.component.html',
  styleUrls: ['./auth.component.scss'],
  encapsulation: ViewEncapsulation.None
})
export class AuthComponent implements OnInit {
  backgrounds = ['login-bg-1.jpg'];
  background: string;

  constructor() {
    this.background = `url("./assets/images/backgrounds/${this.backgrounds[Math.floor(Math.random() * this.backgrounds.length)]
      }")`;
  }

  ngOnInit(): void {
  }

}
