export type StandardIcon =
  | "settings"
  | "add"
  | "delete"
  | "home"
  | "menu"
  | "search"
  | "edit"
  | "save"
  | "close"
  | "arrow_back"
  | "arrow_forward"
  | "refresh"
  | "check"
  | "info"
  | "help"
  | "favorite";

export type AppIcon = StandardIcon | (string & {});