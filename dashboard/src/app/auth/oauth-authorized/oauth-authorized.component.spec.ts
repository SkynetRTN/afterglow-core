import { ComponentFixture, TestBed } from '@angular/core/testing';

import { OauthAuthorizedComponent } from './oauth-authorized.component';

describe('OauthAuthorizedComponent', () => {
  let component: OauthAuthorizedComponent;
  let fixture: ComponentFixture<OauthAuthorizedComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ OauthAuthorizedComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(OauthAuthorizedComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
