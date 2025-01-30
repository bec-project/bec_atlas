import { Component, inject } from '@angular/core';
import { MatCheckbox, MatCheckboxChange } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import {
  MatDialogModule,
  MatDialogRef,
  MAT_DIALOG_DATA,
} from '@angular/material/dialog';

// Models
export interface ColumnModel {
  name: string;
  selected: boolean;
}
@Component({
  selector: 'app-column-selection-dialog',
  imports: [MatCheckbox, MatDialogModule, MatIconModule, MatButtonModule],
  templateUrl: './column-selection-dialog.component.html',
  styleUrl: './column-selection-dialog.component.scss',
})
export class ColumnSelectionDialogComponent {
  columns = inject<ColumnModel[]>(MAT_DIALOG_DATA);
  initialSelection: string[] = [];
  readonly dialogRef = inject(MatDialogRef<ColumnSelectionDialogComponent>);

  handleCheckboxChecked(event: MatCheckboxChange, index: number): void {
    this.columns[index].selected = event.checked;
  }

  onCancelClick(): void {
    this.dialogRef.close(null);
  }

  onApplyClick(): void {
    let data = this.columns
      .filter((column) => column.selected)
      .map((column) => column.name);
    this.dialogRef.close(data);
  }
}
