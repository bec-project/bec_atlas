import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  CompactType,
  DisplayGrid,
  GridsterComponent,
  GridsterConfig,
  GridsterItem,
  GridsterItemComponent,
  GridType,
} from 'angular-gridster2';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
  imports: [CommonModule, GridsterItemComponent, GridsterComponent],
})
export class DashboardComponent implements OnInit {
  dashboard: Array<GridsterItem>;

  options: GridsterConfig = {
    gridType: GridType.Fit,
    compactType: CompactType.None,
    margin: 1,
    outerMargin: true,
    outerMarginTop: null,
    outerMarginRight: null,
    outerMarginBottom: null,
    outerMarginLeft: null,
    useTransformPositioning: true,
    mobileBreakpoint: 640,
    minCols: 40,
    maxCols: 40,
    minRows: 20,
    maxRows: 20,
    minColWidth: 300,
    maxItemCols: 100,
    minItemCols: 1,
    maxItemRows: 100,
    minItemRows: 1,
    maxItemArea: 2500,
    minItemArea: 1,
    defaultItemCols: 1,
    defaultItemRows: 1,
    // fixedColWidth: 105,
    // fixedRowHeight: 105,
    keepFixedHeightInMobile: false,
    keepFixedWidthInMobile: false,
    scrollSensitivity: 50,
    scrollSpeed: 20,
    enableEmptyCellClick: false,
    enableEmptyCellContextMenu: false,
    enableEmptyCellDrop: false,
    enableEmptyCellDrag: false,
    enableOccupiedCellDrop: false,
    emptyCellDragMaxCols: 50,
    emptyCellDragMaxRows: 50,
    ignoreMarginInRow: false,
    draggable: {
      enabled: true,
    },
    resizable: {
      enabled: true,
    },
    swap: true,
    pushItems: true,
    disablePushOnDrag: false,
    disablePushOnResize: false,
    pushDirections: { north: true, east: true, south: true, west: true },
    pushResizeItems: false,
    displayGrid: DisplayGrid.None,
    disableWindowResize: false,
    disableWarnings: false,
    scrollToNewItems: false,
  };

  optionsEdit: GridsterConfig;
  toolbarOptions: GridsterConfig;

  constructor() {
    this.dashboard = [];
    this.optionsEdit = JSON.parse(JSON.stringify(this.options));
    this.toolbarOptions = JSON.parse(JSON.stringify(this.options));
  }

  ngOnInit(): void {
    this.optionsEdit = JSON.parse(JSON.stringify(this.options)); // seriously??? I cannot believe that's the only way to perform a deep copy of an object
    this.optionsEdit.draggable = { enabled: true };
    this.optionsEdit.resizable = { enabled: true };
    this.optionsEdit.displayGrid = DisplayGrid.Always;
    this.toolbarOptions.minCols = 40;
    this.toolbarOptions.maxCols = 40;
    this.toolbarOptions.minRows = 1;
    this.toolbarOptions.maxRows = 1;

    this.dashboard = [
      { cols: 2, rows: 1, y: 0, x: 0 },
      { cols: 2, rows: 2, y: 0, x: 2, hasContent: true },
      { cols: 1, rows: 1, y: 0, x: 4 },
      { cols: 1, rows: 1, y: 2, x: 5 },
      { cols: 1, rows: 1, y: 1, x: 0 },
      { cols: 1, rows: 1, y: 1, x: 0 },
      {
        cols: 2,
        rows: 2,
        y: 3,
        x: 5,
        minItemRows: 2,
        minItemCols: 2,
        label: 'Min rows & cols = 2',
      },
      {
        cols: 2,
        rows: 2,
        y: 2,
        x: 0,
        maxItemRows: 2,
        maxItemCols: 2,
        label: 'Max rows & cols = 2',
      },
      {
        cols: 2,
        rows: 1,
        y: 2,
        x: 2,
        dragEnabled: true,
        resizeEnabled: true,
        label: 'Drag&Resize Enabled',
      },
      {
        cols: 1,
        rows: 1,
        y: 2,
        x: 4,
        dragEnabled: false,
        resizeEnabled: false,
        label: 'Drag&Resize Disabled',
      },
      { cols: 1, rows: 1, y: 2, x: 6 },
    ];

    console.log('DashboardComponent initialized');
  }
}
