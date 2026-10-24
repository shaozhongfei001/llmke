export interface SectionType {
  id?: number;
  articleTypeID?: number;
  articleID?: number; // 文章配置时使用
  sectionPrompt?: string;
  sectionContentExample?: string;
  materialType?: number[];
  content?: string;
  hasSectionPrompt?: boolean;
  hasContent?: boolean;
}

export interface ContentSourceType {
  sourceType: string;
  materialTypeIds?: number[];
  refIds: string[];
  refNames: string[];
}

export interface OutlineType {
  id: string;
  title?: string;
  contentSources?: ContentSourceType[] | null;
  sectionId?: number;
  section?: SectionType;
  children?: OutlineType[];
  subParagraphs?: OutlineType[];
  extraInfo?: any;
  relatedMaterials?: Map<
    number,
    {
      fileId: number;
      fileName: string;
    }[]
  >;
  contentOperation?: "0" | "1"; //生成文章时，大纲是否被选中
  placeholder?: string;
  depth?: number;
  pardenId?: string | undefined;
  isLeaf?: boolean;
  isExpand?: boolean | undefined;
  dependency?: any[];
  useCustomDB?: boolean;
  useCustomKb?: boolean;
}

export interface MaterialItemType {
  id: number;
  fileName: string;
  state: number;
  material_type: number[];
}

export interface MaterialType {
  id: number;
  name: string;
  parentID: number;
  gmtCreate: string;
  subTypeList?: MaterialType[];
}
