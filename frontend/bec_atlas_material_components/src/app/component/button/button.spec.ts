import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

import { Button } from './button';

describe('Button', () => {
  let component: Button;
  let fixture: ComponentFixture<Button>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Button, MatButtonModule, MatIconModule],
    }).compileComponents();

    fixture = TestBed.createComponent(Button);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  const getButtonElement = (): HTMLButtonElement =>
    fixture.nativeElement.querySelector('button');

  const setInput = (name: keyof Button, value: unknown): void => {
    fixture.componentRef.setInput(name as string, value);
    fixture.detectChanges();
  };

  it('renders label text when provided', () => {
    setInput('label', 'Launch');

    expect(getButtonElement().textContent).toContain('Launch');
  });

  it('hides the label when showLabel is false', () => {
    setInput('label', 'Launch');
    setInput('showLabel', false);

    expect(
      getButtonElement().querySelector('.app-button__label')
    ).toBeNull();
  });

  it('emits clicked output when pressed', () => {
    const clickSpy = vi.spyOn(component.clicked, 'emit');
    fixture.detectChanges();

    getButtonElement().click();

    expect(clickSpy).toHaveBeenCalledTimes(1);
  });

  it('toggles its state and emits toggledChange when configured', () => {
    setInput('togglable', true);
    const toggleSpy = vi.spyOn(component.toggledChange, 'emit');

    getButtonElement().click();

    expect(component.isToggled()).toBeTruthy();
    expect(toggleSpy).toHaveBeenCalledWith(true);
  });

  it('prevents interaction when disabled', () => {
    setInput('togglable', true);
    setInput('disabled', true);
    const toggleSpy = vi.spyOn(component.toggledChange, 'emit');
    const clickSpy = vi.spyOn(component.clicked, 'emit');

    getButtonElement().click();

    expect(toggleSpy).not.toHaveBeenCalled();
    expect(clickSpy).not.toHaveBeenCalled();
    expect(component.isToggled()).toBeFalsy();
  });
});
