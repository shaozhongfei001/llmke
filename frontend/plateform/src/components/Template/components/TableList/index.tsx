import {
  Button,
  Switch,
  Popconfirm,
  Tag,
  Table,
  theme,
  Typography
} from "antd";
import { ColumnTypes, DataType, EditableCell, EditableRow } from "./editTable";
import { uid } from "uid";
import type { DragEndEvent } from "@dnd-kit/core";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors
} from "@dnd-kit/core";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import {
  arrayMove,
  SortableContext,
  useSortable,
  verticalListSortingStrategy
} from "@dnd-kit/sortable";
import { useEffect } from "react";
import { TypeOptions } from "../../core/constants";
import { InitCount } from "../../core/useStateStore";
export const generateRow = (dataIndex: string) => {
  return {
    key: uid(),
    dataIndex: dataIndex,
    title: dataIndex,
    required: false,
    type: "string"
  };
};
const { useToken } = theme;
const tags = [
  {
    key: uid(),
    dataIndex: "reportName",
    title: "报告标题",
    required: false,
    type: "string"
  },
  {
    key: uid(),
    dataIndex: "reportingTime",
    title: "报告日期",
    required: false,
    type: "date"
  }
];
const TableList = ({
  tableList,
  setTableList,
  supportOutlines,
  isVersion = false
}: any) => {
  const { token } = useToken();
  const defaultColumns: (ColumnTypes[number] & {
    editable?: boolean;
    dataIndex: string;
  })[] = [
    {
      title: "变量",
      dataIndex: "dataIndex",
      editable: !isVersion,
      ellipsis: true,
      render: (_, record) => {
        return _;
      }
    },
    {
      title: "显示名称",
      dataIndex: "title",
      editable: !isVersion,
      ellipsis: true
    },
    {
      title: "类型",
      dataIndex: "type",
      editable: !isVersion,
      render: (_, record) => {
        return TypeOptions.filter((item) => item.value === _).map(
          (v) => v.label
        );
      }
    },
    {
      title: "默认参数",
      dataIndex: "defaultValue",
      editable: !isVersion,
      ellipsis: true
    },
    {
      title: "必填项",
      dataIndex: "required",
      editable: !isVersion
    },
    {
      title: "操作",
      dataIndex: "operation",
      render: (_, record: any) =>
        tableList.length >= 1 ? (
          <Popconfirm
            title="确定删除？"
            cancelText="取消"
            okText="确定"
            cancelButtonProps={{
              style: {
                borderRadius: "4px",
                color: "#555",
                borderColor: "#EEEEEE"
              }
            }}
            okButtonProps={{
              style: {
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                border: "none",
                borderRadius: "4px"
              }
            }}
            overlayInnerStyle={{
              width: "224px"
            }}
            onConfirm={() => handleDelete(record.key)}
          >
            <Button
              type="link"
              disabled={record.key === InitCount || isVersion}
            >
              删除
            </Button>
          </Popconfirm>
        ) : null
    }
  ];
  const item: any = defaultColumns.find((i: any) => i.dataIndex === "required");
  if (isVersion) {
    item.render = (val: boolean) => {
      return <Switch disabled={true} checked={val} />;
    };
  }

  useEffect(() => {
    if (supportOutlines) {
      // 如果支持大纲的话，内容描述必须有
      const re = tableList.find((d: any) => d.dataIndex == "contentAbstract");
      if (!re) {
        setTableList([
          ...tableList,
          {
            key: uid(),
            dataIndex: "contentAbstract",
            title: "内容描述",
            required: true,
            type: "longString"
          }
        ]);
      }
    }
  }, [supportOutlines]);
  const handleDelete = (key: React.Key) => {
    const newData = tableList.filter((item: any) => item.key !== key);
    setTableList(newData);
  };
  const handleAdd = (data: DataType) => {
    const newData = [...tableList];
    const index = newData.findIndex((item) => data.key === item.key);
    if (index < 0) {
      setTableList([...tableList, data]);
    }
  };
  const handleSave = (row: DataType) => {
    const newData = [...tableList];
    const index = newData.findIndex((item) => row.key === item.key);
    const item = newData[index];
    newData.splice(index, 1, {
      ...item,
      ...row
    });
    console.log("---save cell---", newData);
    setTableList(newData);
  };
  const columns = defaultColumns.map((col) => {
    if (!col.editable) {
      return col;
    }
    return {
      ...col,
      onCell: (record: DataType) => ({
        record,
        editable: col.editable,
        dataIndex: col.dataIndex,
        title: col.title,
        handleSave
      })
    };
  });

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        // https://docs.dndkit.com/api-documentation/sensors/pointer#activation-constraints
        distance: 1
      }
    })
  );

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (active.id !== over?.id) {
      const prev = tableList;
      const activeIndex = prev.findIndex((i: any) => i.key === active.id);
      const overIndex = prev.findIndex((i: any) => i.key === over?.id);
      setTableList(arrayMove(prev, activeIndex, overIndex));
    }
  };

  return (
    <div>
      <DndContext
        sensors={sensors}
        modifiers={[restrictToVerticalAxis]}
        onDragEnd={onDragEnd}
      >
        <SortableContext
          // rowKey array
          items={tableList.map((i: any) => i.key)}
          strategy={verticalListSortingStrategy}
        >
          <Table
            components={{
              body: {
                row: EditableRow,
                cell: EditableCell
              }
            }}
            style={{
              width: "100%"
            }}
            size="small"
            rowClassName={() => "editable-row"}
            dataSource={tableList}
            columns={columns as ColumnTypes}
            pagination={false}
          />
        </SortableContext>
      </DndContext>

      <div className="mt-[10px]">
        <label className="mr-2 text-sm">常用变量</label>
        {tags.map((tag: DataType) => {
          return (
            <Tag
              key={tag.key}
              bordered={false}
              color="processing"
              className={`${isVersion ? "opacity-80" : "cursor-pointer"} text-[#055AFF] mr-2`}
              onClick={() => (isVersion ? null : handleAdd(tag))}
            >
              {tag.title}
            </Tag>
          );
        })}
      </div>
    </div>
  );
};
export default TableList;
