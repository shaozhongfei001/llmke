export type OutlineItemLocation = 'top' | 'center' | 'bottom';

export interface ItemInfo {
  depth: number;
  location: OutlineItemLocation;
  onlyOne: boolean;
}
