import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule } from '@angular/common/http';  // <- Cet import est crucial
import { AppRoutingModule } from './app.routes';
import { AppComponent } from './app.component';

@NgModule({
  declarations: [
    AppComponent
    // Vos autres composants
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule  // <- TRÈS IMPORTANT : doit être dans imports
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }