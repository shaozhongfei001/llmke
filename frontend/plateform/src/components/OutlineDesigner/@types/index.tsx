export type OutlineData = {
  id: string;
  title: string;
  contentAbstract?: string;
  sources?: string[];
  children?: OutlineData[];
};

export interface OutlinesDsignerProps {
  outlineData?: OutlineData[];
  outlinesEventEmit: (title: string, data: any) => void;
  limit?: number;
}
