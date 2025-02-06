import { Component } from '@angular/core';
import {
  GridstackComponent,
  GridstackItemComponent,
  NgGridStackOptions,
} from 'gridstack/dist/angular';
import { CommonModule } from '@angular/common';
import { GridStackOptions } from 'gridstack';

@Component({
  selector: 'app-overview-grid',
  imports: [GridstackComponent, GridstackItemComponent, CommonModule],
  templateUrl: './overview-grid.component.html',
  styleUrl: './overview-grid.component.scss',
})
export class OverviewGridComponent {
  public gridOptions: NgGridStackOptions = {
    margin: 1,
    minRow: 8, // make space for empty message
    // staticGrid: true,
    cellHeight: 100,
    float: true,
    columnOpts: {
      breakpointForWindow: true,
      breakpoints: [
        { w: 800, c: 1 },
        { w: 1000, c: 10 },
      ],
    },
    disableResize: true,
    disableDrag: true,
    children: [
      // or call load()/addWidget() with same data
      {
        x: 1,
        y: 5,
        minW: 1,
        selector: 'app-device-box',
        input: { device: 'samx', signal_name: 'samx' },
      },
      {
        x: 2,
        y: 5,
        minW: 1,
        selector: 'app-device-box',
        input: { device: 'samy', signal_name: 'samy' },
      },
      {
        x: 0,
        y: 0,
        minW: 12,
        minH: 3,
        selector: 'app-queue-table',
      },
      // {x:1, y:0, minW:2, selector:'app-a', input: { text: 'bar' }}, // custom input that works using BaseWidget.deserialize() Object.assign(this, w.input)
      // {x:2, y:0, selector:'app-b'},
      { x: 3, y: 0, content: 'plain html' },
    ],
  };
}
