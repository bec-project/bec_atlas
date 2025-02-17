import { Injectable } from '@angular/core';
import { shareReplay, timeout } from 'rxjs/operators';
import { tap } from 'rxjs/operators';
import { AuthDataService } from './remote-data.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  forceReload = false;
  constructor(private dataService: AuthDataService) {}

  login(principal: string, password: string) {
    return this.dataService.login(principal, password).pipe(
      timeout(3000),
      tap((res) => {
        this.setSession(res);
      }),
      shareReplay()
    );
  }

  setSession(authResult: string) {
    // it would be good to get an expiration date for the token...
    localStorage.setItem('id_session', this.getRandomId());
  }

  logout() {
    this.dataService.logout();
    localStorage.removeItem('id_session');
    this.forceReload = true;
  }

  getRandomId() {
    return Math.floor(Math.random() * 1000 + 1).toString();
  }
}
