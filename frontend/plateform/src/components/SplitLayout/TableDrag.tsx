import React, { useState, useCallback, useRef } from "react";
import { Table, Tag, Button, Popconfirm, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useDrag, useDrop } from "react-dnd";
import { HTML5Backend } from "react-dnd-html5-backend";
import { DndProvider } from "react-dnd";
import { MenuOutlined } from "@ant-design/icons";
import "./tableDrag.css";

interface DataType {
  key: string;
  name: string;
  type: "folder" | "file";
  size: string;
  modified: string;
  tags: string[];
  children?: DataType[];
}

const data: DataType[] = [
  {
    key: "1",
    name: "项目文档",
    type: "folder",
    size: "-",
    modified: "2023-06-15",
    tags: ["重要"],
    children: [
      {
        key: "1-1",
        name: "需求文档",
        type: "folder",
        size: "-",
        modified: "2023-06-10",
        tags: ["进行中"],
        children: [
          {
            key: "1-1-1",
            name: "功能需求.docx",
            type: "file",
            size: "1.2MB",
            modified: "2023-06-05",
            tags: ["文档"]
          },
          {
            key: "1-1-2",
            name: "UI设计需求.pdf",
            type: "file",
            size: "2.3MB",
            modified: "2023-06-07",
            tags: ["设计"]
          }
        ]
      },
      {
        key: "1-2",
        name: "设计文档",
        type: "folder",
        size: "-",
        modified: "2023-06-12",
        tags: ["审核中"],
        children: [
          {
            key: "1-2-1",
            name: "界面设计.psd",
            type: "file",
            size: "5.7MB",
            modified: "2023-06-08",
            tags: ["设计"]
          },
          {
            key: "1-2-2",
            name: "交互设计说明.docx",
            type: "file",
            size: "0.9MB",
            modified: "2023-06-09",
            tags: ["文档"]
          }
        ]
      }
    ]
  },
  {
    key: "2",
    name: "开发资源",
    type: "folder",
    size: "-",
    modified: "2023-06-18",
    tags: ["开发"],
    children: [
      {
        key: "2-1",
        name: "前端资源",
        type: "folder",
        size: "-",
        modified: "2023-06-15",
        tags: ["前端"],
        children: [
          {
            key: "2-1-1",
            name: "组件库",
            type: "folder",
            size: "-",
            modified: "2023-06-10",
            tags: ["组件"],
            children: [
              {
                key: "2-1-1-1",
                name: "Button.tsx",
                type: "file",
                size: "12KB",
                modified: "2023-06-08",
                tags: ["TS"]
              },
              {
                key: "2-1-1-2",
                name: "Modal.tsx",
                type: "file",
                size: "18KB",
                modified: "2023-06-09",
                tags: ["TS"]
              }
            ]
          },
          {
            key: "2-1-2",
            name: "utils.js",
            type: "file",
            size: "8KB",
            modified: "2023-06-12",
            tags: ["工具"]
          }
        ]
      },
      {
        key: "2-2",
        name: "后端资源",
        type: "folder",
        size: "-",
        modified: "2023-06-16",
        tags: ["后端"],
        children: [
          {
            key: "2-2-1",
            name: "API文档.md",
            type: "file",
            size: "15KB",
            modified: "2023-06-14",
            tags: ["文档"]
          },
          {
            key: "2-2-2",
            name: "数据库设计.sql",
            type: "file",
            size: "7KB",
            modified: "2023-06-15",
            tags: ["数据库"]
          }
        ]
      }
    ]
  },
  {
    key: "3",
    name: "会议记录",
    type: "folder",
    size: "-",
    modified: "2023-06-20",
    tags: ["会议"],
    children: [
      {
        key: "3-1",
        name: "项目启动会.docx",
        type: "file",
        size: "0.5MB",
        modified: "2023-05-30",
        tags: ["文档"]
      },
      {
        key: "3-2",
        name: "设计评审会.pptx",
        type: "file",
        size: "1.8MB",
        modified: "2023-06-05",
        tags: ["演示"]
      }
    ]
  }
];

const DRAG_TYPE = "TABLE_ROW";

const TreeTable: React.FC = () => {
  const [dataSource, setDataSource] = useState<DataType[]>(data);
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([]);

  // 展开/折叠所有行
  const toggleExpandAll = () => {
    if (expandedRowKeys.length > 0) {
      setExpandedRowKeys([]);
    } else {
      const allKeys: string[] = [];
      const getAllKeys = (data: DataType[]) => {
        data.forEach((item) => {
          allKeys.push(item.key);
          if (item.children && item.children.length > 0) {
            getAllKeys(item.children);
          }
        });
      };
      getAllKeys(dataSource);
      setExpandedRowKeys(allKeys);
    }
  };

  // 查找节点及其父节点
  const findNode = (
    key: string,
    nodes: DataType[]
  ): { node: DataType; parent: DataType[] } | null => {
    for (const node of nodes) {
      if (node.key === key) {
        return { node, parent: nodes };
      }
      if (node.children && node.children.length > 0) {
        const found = findNode(key, node.children);
        if (found) return found;
      }
    }
    return null;
  };

  // 处理拖拽放置
  const handleDrop = (
    draggedKey: string,
    targetKey: string,
    position: "before" | "after" | "child"
  ) => {
    const result = findNode(draggedKey, dataSource);
    if (!result) return;

    const { node: draggedNode, parent: sourceParent } = result;
    const targetResult = findNode(targetKey, dataSource);
    if (!targetResult) return;

    const { node: targetNode, parent: targetParent } = targetResult;

    // 从源位置移除节点
    const sourceIndex = sourceParent.findIndex(
      (item) => item.key === draggedKey
    );
    sourceParent.splice(sourceIndex, 1);

    // 添加到目标位置
    switch (position) {
      case "before":
      case "after":
        const targetIndex = targetParent.findIndex(
          (item) => item.key === targetKey
        );
        const insertIndex =
          position === "before" ? targetIndex : targetIndex + 1;
        targetParent.splice(insertIndex, 0, draggedNode);
        break;

      case "child":
        if (!targetNode.children) {
          targetNode.children = [];
        }
        targetNode.children.push(draggedNode);
        break;
    }

    setDataSource([...dataSource]);
  };

  // 删除节点
  const handleDelete = (key: string) => {
    const deleteNode = (nodes: DataType[]): DataType[] => {
      return nodes.filter((node) => {
        if (node.key === key) return false;
        if (node.children && node.children.length > 0) {
          node.children = deleteNode(node.children);
        }
        return true;
      });
    };

    setDataSource(deleteNode(dataSource));
    message.success("节点已删除");
  };

  const columns: ColumnsType<DataType> = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      width: 300,
      render: (text, record) => (
        <div className="name-cell">
          {record.type === "folder" ? (
            <span className="folder-icon">📁</span>
          ) : (
            <span className="file-icon">📄</span>
          )}
          <span>{text}</span>
        </div>
      )
    },
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      width: 100,
      render: (text) => (
        <Tag color={text === "folder" ? "blue" : "green"}>
          {text === "folder" ? "文件夹" : "文件"}
        </Tag>
      )
    },
    {
      title: "大小",
      dataIndex: "size",
      key: "size",
      width: 100,
      align: "right"
    },
    {
      title: "修改日期",
      dataIndex: "modified",
      key: "modified",
      width: 150
    },
    {
      title: "标签",
      dataIndex: "tags",
      key: "tags",
      render: (tags: string[]) => (
        <span>
          {tags.map((tag) => (
            <Tag key={tag} color="geekblue">
              {tag}
            </Tag>
          ))}
        </span>
      )
    },
    {
      title: "操作",
      key: "action",
      width: 120,
      render: (_, record) => (
        <Popconfirm
          title="确定要删除吗？"
          onConfirm={() => handleDelete(record.key)}
          okText="确定"
          cancelText="取消"
        >
          <Button type="link" danger size="small">
            删除
          </Button>
        </Popconfirm>
      )
    }
  ];

  // 可拖拽行组件
  const DraggableRow = ({ index, record, moveRow, ...restProps }: any) => {
    const ref = useRef<HTMLTableRowElement>(null);
    const [{ isOver, dropPosition }, drop] = useDrop({
      accept: DRAG_TYPE,
      collect: (monitor) => {
        const { key: dragKey } = monitor.getItem() || {};
        if (dragKey === record.key) {
          return {};
        }
        return {
          isOver: monitor.isOver(),
          dropPosition: monitor.getClientOffset()?.y
        };
      },
      drop: (item: { key: string }) => {
        if (!ref.current) return;

        // 计算鼠标在目标行中的相对位置
        const rect = ref.current.getBoundingClientRect();
        const relativeY = (dropPosition || 0) - rect.top;
        const height = rect.height;

        // 根据位置判断放置类型
        let position: "before" | "after" | "child" = "child";

        if (relativeY < height * 0.25) {
          // 在前1/4区域
          if (relativeY < height * 0.125) {
            position = "before";
          } else {
            position = "after";
          }
        }

        moveRow(item.key, record.key, position);
      }
    });

    const [{ isDragging }, drag, preview] = useDrag({
      type: DRAG_TYPE,
      item: { key: record.key },
      collect: (monitor) => ({
        isDragging: monitor.isDragging()
      })
    });

    drop(drag(ref));

    // 根据拖拽位置设置样式
    const positionIndicator = () => {
      if (!isOver || !dropPosition || !ref.current) return null;

      const rect = ref.current.getBoundingClientRect();
      const relativeY = dropPosition - rect.top;
      const height = rect.height;

      if (relativeY < height * 0.25) {
        if (relativeY < height * 0.125) {
          return <div className="drop-indicator top" />;
        } else {
          return <div className="drop-indicator bottom" />;
        }
      }
      return <div className="drop-indicator child" />;
    };

    return (
      <tr
        ref={ref}
        {...restProps}
        className={`draggable-row ${isDragging ? "dragging" : ""} ${isOver ? "over" : ""}`}
      >
        {positionIndicator()}
        <td className="drag-handle">
          <MenuOutlined className="drag-icon" />
        </td>
        {restProps.children}
      </tr>
    );
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="tree-table-container">
        <div className="header">
          <h1>可拖拽树形表格</h1>
          <p>支持展开/折叠、表头对齐和行拖拽功能</p>
        </div>

        <div className="controls">
          <Button type="primary" onClick={toggleExpandAll}>
            {expandedRowKeys.length > 0 ? "折叠全部" : "展开全部"}
          </Button>
          <div className="instructions">
            <Tag color="blue">拖拽提示</Tag>
            <span>拖拽行时根据位置放置：</span>
            <span className="before-hint">顶部1/8区域 - 放在前面</span>
            <span className="after-hint">顶部1/4区域 - 放在后面</span>
            <span className="child-hint">其余区域 - 作为子项</span>
          </div>
        </div>

        <Table
          className="tree-table"
          columns={[
            {
              title: "操作",
              key: "drag",
              width: 50,
              render: () => <MenuOutlined className="drag-icon" />
            },
            ...columns
          ]}
          dataSource={dataSource}
          rowKey="key"
          size="middle"
          pagination={false}
          scroll={{ y: 500 }}
          expandable={{
            expandedRowKeys,
            onExpand: (expanded, record) => {
              if (expanded) {
                setExpandedRowKeys([...expandedRowKeys, record.key]);
              } else {
                setExpandedRowKeys(
                  expandedRowKeys.filter((key) => key !== record.key)
                );
              }
            },
            indentSize: 20
          }}
          components={{
            body: {
              row: (props: any) => (
                <DraggableRow
                  {...props}
                  record={
                    props["data-row-key"] &&
                    findNode(props["data-row-key"], dataSource)?.node
                  }
                  moveRow={handleDrop}
                />
              )
            }
          }}
        />

        <div className="features">
          <h3>功能特点</h3>
          <ul>
            <li>树形结构展示 - 支持多级嵌套文件夹结构</li>
            <li>行拖拽功能 - 可拖拽行到其他位置</li>
            <li>智能位置检测 - 根据鼠标位置自动判断放置位置</li>
            <li>展开/折叠 - 可展开或折叠文件夹查看内容</li>
            <li>对齐表头 - 所有列严格对齐表头</li>
            <li>响应式设计 - 适应不同屏幕尺寸</li>
            <li>视觉反馈 - 拖拽时有明显的视觉指示</li>
          </ul>
        </div>
      </div>
    </DndProvider>
  );
};

export default TreeTable;
