export interface ModelItem {
  id: string;
  modelIde: string;
  modelName: string;
  type: string;
  dec: string;
  status: "available" | "unavailable" | "limited";
  apiKey?: string;
  url?: string;
  isPublic?: boolean;
  isVisibleToAll?: boolean;
  permission: number;
  thinking?: boolean;
  trace?: boolean;
}

export interface Collaborator {
  id: string;
  name: string;
  role: string;
  permission: string;
  avatar?: string;
}

export type DrawerType = "add" | "edit" | "auth";
