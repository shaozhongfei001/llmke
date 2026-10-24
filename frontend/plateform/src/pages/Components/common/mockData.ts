import { uid } from "uid";

function addPid(data: any[], parentId: string | null = null): any[] {
  return data.map((item) => {
    const newItem = { ...item, pid: parentId };
    if (item.children) {
      newItem.children = addPid(item.children, newItem.id);
    }
    return newItem;
  });
}

const DepartmentData = addPid([
  {
    id: "1",
    name: "部门名称1",
    type: "department",
    status: 0,
    children: [
      {
        id: "1-1",
        name: "陈晓明1",
        department: "市场部",
        status: 0
      },
      {
        id: "1-2",
        name: "陈晓明2",
        department: "市场部",
        status: 1
      },
      {
        id: "1-3",
        name: "市场部",
        type: "department",
        status: 1,
        children: [
          {
            id: "1-3-1",
            name: "王小明",
            department: "市场部",
            status: 0
          },
          {
            id: "1-3-2",
            name: "张小明",
            department: "市场部",
            status: 1
          },
          {
            id: "1-3-3",
            name: "市场攻坚部",
            type: "department",
            status: 1,
            children: [
              {
                id: "1-3-3-1",
                name: "李晓红",
                department: "市场攻坚部",
                status: 0
              }
            ]
          }
        ]
      }
    ]
  },
  {
    id: "2",
    name: "部门名称2",
    type: "department",
    status: 2,
    children: [
      {
        id: "2-1",
        name: "张三",
        status: 0
      },
      {
        id: "2-2",
        name: "李四",
        status: 0
      }
    ]
  },
  {
    id: uid(),
    name: "部门名称",
    type: "department",
    status: 0
  },
  {
    id: uid(),
    name: "陈晓明",
    status: 0
  },
  {
    id: uid(),
    name: "陈晓明1",
    status: 0
  },
  {
    id: uid(),
    name: "陈晓明2",
    status: 0
  },
  {
    id: uid(),
    name: "陈晓明3",
    status: 0
  },
  {
    id: uid(),
    name: "陈晓明4",
    status: 0
  },
  {
    id: uid(),
    name: "陈晓明5",
    status: 0
  },
  {
    id: uid(),
    name: "陈晓明6",
    status: 0
  },
  {
    id: uid(),
    name: "陈晓明7",
    status: 0
  },
  {
    id: uid(),
    name: "陈晓明8",
    status: 0
  },
  {
    id: uid(),
    name: "陈晓明9",
    status: 0
  },
  {
    id: uid(),
    name: "陈晓明0",
    status: 0
  },
  {
    id: uid(),
    name: "陈晓明10",
    status: 0
  },
  {
    id: uid(),
    name: "部门名称",
    type: "department",
    status: 0
  },
  {
    id: uid(),
    name: "部门名称",
    type: "department",
    status: 0
  },
  {
    id: uid(),
    name: "部门名称",
    type: "department",
    status: 0
  },
  {
    id: uid(),
    name: "部门名称",
    type: "department",
    status: 0
  }
]);

const GroupData = [
  {
    id: uid(),
    name: "用户组1",
    type: "group",
    status: 0
  },
  {
    id: uid(),
    name: "用户组2",
    type: "group",
    status: 0
  },
  {
    id: uid(),
    name: "用户组3",
    type: "group",
    status: 0
  }
];

export const MockDepartmentData = [
  {
    id: uid(),
    hideCheck: true,
    name: "组织架构",
    children: DepartmentData,
    type: "department"
  },
  {
    id: uid(),
    hideCheck: true,
    name: "用户组",
    children: GroupData,
    type: "department"
  }
];
