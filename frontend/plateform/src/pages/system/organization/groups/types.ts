export interface GroupInfo {
  id: string;
  name: string;
  description?: string;
  parentId?: string;
  members?: GroupMember[];
  createBy?: string;
  gmtCreate?: string;
  gmtModified?: string;
}

export interface GroupMember {
  id: string;
  name: string;
  email: string;
  departmentName: string;
  type: 'user' | 'department';
}

export interface GroupFormData {
  name: string;
  description?: string;
  parentId?: string;
} 