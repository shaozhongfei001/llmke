import { ReactElement } from "react";

export type Middleware = (props: any) => boolean;
export interface RouteItem {
  key?: number;
  path: string;
  exact?: boolean;
  strict?: boolean;
  index?: boolean;
  element?: React.ReactElement;  // changed from 'component'
  alive?: boolean;
  middleware?: Middleware[];
  meta?: Record<string, any>;
  children?: RouteItem[];
}