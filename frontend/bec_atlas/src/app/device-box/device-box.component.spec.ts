import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DeviceBoxComponent } from './device-box.component';

describe('DeviceBoxComponent', () => {
  let component: DeviceBoxComponent;
  let fixture: ComponentFixture<DeviceBoxComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DeviceBoxComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DeviceBoxComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
