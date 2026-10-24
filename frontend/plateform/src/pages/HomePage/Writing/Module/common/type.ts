import type { DataNode, TreeProps } from "antd/es/tree";
export interface ITreeNode extends DataNode {
  parentId?: string;
  hasSectionPrompt?: boolean;
  level?: number;
  // status: number;
}

export interface IListItem {
  id: string;
  title: string;
  path?: string;
}
export interface ISection {
  sectionTitle?: string; //章节标题
  sectionPrompt?: string;
  sectionContentExample?: string; //参考示例
  description?: string; //描述信息
  gmtModified?: string; //最后修改时间
}

export interface IChapterTreeItem {
  id: number; //新增时不传递
  rootId: number; //根节点id。根节点的该值等于id
  rootTitle: string; //根节点title
  parentId: number; //父节点id
  sectionTitle: string; //章节标题
  sectionPrompt: string; //内容要求
  sectionContentExample: string; //参考示例
  description: string; //描述信息
  hasSectionPrompt: boolean; // 是否写过内容要求
  sort_no: number; //排序编号，前端不能修改，只是查看
  subSections: IChapterTreeItem[]; //子章节
}

export interface IChapterListItem {
  id: number;
  parentId: number;
  rootId: number;
  rootTitle: string;
  sectionTitle: string;
  sortNo: number;
  status: number;
}

export interface IAnalysis {
  categoryId: string;
  creatorId?: string;
  gmtCreate?: string;
  gmtModified?: string;
  id: string;
  modifiedBy?: string;
  name: string;
  status: number;
  state: number;
  description?: string;
  systemPrompt?: string;
  userPrompt?: string;
  categories?: any[];
}

export interface IAnalysisCategoryTreeItem {
  categoryName: string;
  creatorId?: string;
  gmtCreate?: string;
  gmtModified?: string;
  id: string;
  modifiedBy?: string;
  parentId?: string;
  status?: 1;
  subCategories?: IAnalysisCategoryTreeItem[];
  path?: string[];
}
