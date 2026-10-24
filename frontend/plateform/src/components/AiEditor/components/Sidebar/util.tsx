import { uid } from "uid";
import dayjs from "dayjs";
import { Select } from "antd";
interface TreeNode {
  id: number | string;
  children?: TreeNode[];
  [key: string]: any;
}
export const delItemById = (tree: TreeNode[], id: number | string) => {
  return tree.reduce((acc, node) => {
    if (node.id !== id) {
      if (node.children) {
        const filteredChildren = delItemById(node.children, id);
        if (filteredChildren.length !== node.children.length) {
          node.children = filteredChildren;
        }
      }
      acc.push(node);
    }
    return acc;
  }, [] as TreeNode[]);
};

export const addItemById = (tree: TreeNode[], id: number | string) => {
  return tree.reduce((acc, node) => {
    if (node.id !== id) {
      if (node.children) {
        const filteredChildren = addItemById(node.children, id);
        if (filteredChildren.length !== node.children.length) {
          node.children = filteredChildren;
        }
      }
    } else {
      node.children = node?.children
        ? [
            ...node.children,
            {
              id: uid(32),
              title: "未命名标题"
            }
          ]
        : [
            {
              id: uid(32),
              title: "未命名标题"
            }
          ];
    }
    acc.push(node);
    return acc;
  }, [] as TreeNode[]);
};

export const isChildren = (tree, id) => {
  if (!tree) return false;
  return tree.some((node) => {
    if (node.id === id) return true;
    if (node.children) return isChildren(node.children, id);
    return false;
  });
};

export const moveItem = (
  direction: "top" | "bottom",
  { tree, dragItem, dropItem, limit = 3 }
) => {
  const allowMove = !isChildren(dragItem?.children, dropItem.id);
  console.log(allowMove);
  if (!allowMove) return tree;
  const newTree = delItemById(tree, dragItem.id);
  const moveFn = (tree, id) => {
    return tree.reduce((acc, node) => {
      if (node.id !== id) {
        if (node.children) {
          node.children = moveFn(node.children, id);
        }
        acc.push(node);
      } else {
        if (direction === "top") {
          acc.push(dragItem, node);
        } else {
          acc.push(node, dragItem);
        }
      }
      return acc;
    }, [] as TreeNode[]);
  };
  const res = moveFn(newTree, dropItem.id);
  return res;
};

export const changeItemById = ({ tree, value, key, id }) => {
  function updateNestedItemById(data, id, fieldName, newValue) {
    for (let i = 0; i < data.length; i++) {
      if (data[i].id === id) {
        data[i][fieldName] = newValue;
        return true; // 找到并修改后返回true
      }
      if (data[i].children && data[i].children.length > 0) {
        if (updateNestedItemById(data[i].children, id, fieldName, newValue)) {
          return true; // 如果在子数组中找到并修改了，则返回true
        }
      }
    }
    return false; // 没有找到匹配的id
  }
  updateNestedItemById(tree, id, key, value);
  return tree;
};

export const createTemplateForm = (form_schema: any[]) => {
  const formTemplate = form_schema.map((s) => {
    if (s.required == true) {
      s.formItemProps = {
        rules: [
          {
            required: true,
            message: `请填写${s.title}`
          }
        ]
      };
    }
    if (s.defaultValue) {
      if (s.type == "select") {
        s.initialValue = s.defaultValue[0];
      } else {
        s.initialValue = s.defaultValue;
      }
    }

    switch (s.type) {
      case "longString":
        s.valueType = "textarea";
        break;
      case "date":
        {
          const formParams = {
            valueType: "date",
            initialValue: dayjs().format("YYYY[年]MM[月]DD[日]"),
            formItemProps: {
              rules: [{ required: true, message: "请选择发文时间" }],
              // normalize: (value: any) =>
              //   dayjs(value).format("YYYY[年]MM[月]DD[日]"),
              getValueFromEvent: (...[, dateString]) => dateString,
              getValueProps: (value) => ({
                value: value ? dayjs(value, "YYYY[年]MM[月]DD[日]") : undefined
              })
            },
            fieldProps: () => {
              return {
                placeholder: "选择日期",
                style: {
                  width: "100%"
                },
                placement: "bottomRight",
                getPopupContainer: (triggerNode) => triggerNode.parentNode,

                format: (value: any) =>
                  dayjs(value).format("YYYY[年]MM[月]DD[日]")
              };
            }
          };
          s = {
            ...s,
            ...formParams
          };
        }
        break;
      case "select": {
        const opts = s.defaultValue.map((v: string) => {
          return {
            label: v,
            value: v
          };
        });
        s = {
          ...s,
          valueType: "select",
          renderFormItem: () => (
            <Select
              placeholder="请选择"
              options={[...opts]}
              className="w-full"
            />
          )
        };
      }
    }

    s.key = s.dataIndex;
    return s;
  });
  return formTemplate;
};
