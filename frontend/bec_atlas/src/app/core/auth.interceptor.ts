import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpResponse,
  HttpErrorResponse,
} from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

function logout() {
  localStorage.removeItem('id_session');
  location.href = '/login';
}

function handle_request(handler: HttpHandler, req: HttpRequest<any>) {
  return handler.handle(req).pipe(
    tap({
      next: (event: HttpEvent<any>) => {
        if (event instanceof HttpResponse) {
          // console.log(cloned);
          // console.log("Service Response thr Interceptor");
        }
      },
      error: (err: any) => {
        if (err instanceof HttpErrorResponse) {
          console.log('err.status', err);
          if (err.status === 401) {
            logout();
          }
        }
      },
    })
  );
}

@Injectable({
  providedIn: 'root',
})
export class AuthInterceptor implements HttpInterceptor {
  intercept(
    req: HttpRequest<any>,
    next: HttpHandler
  ): Observable<HttpEvent<any>> {
    const cloned = req.clone({
      withCredentials: true,
    });

    return handle_request(next, cloned);
  }
}
