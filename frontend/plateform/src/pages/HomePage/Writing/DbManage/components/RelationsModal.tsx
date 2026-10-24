import { Modal, Button, Space, Select } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import { useState, useEffect, useMemo } from "react";
import plusBlue from "@/assets/img/plusBlue.png";
import mysqlIcon from "@/assets/svg/mysql.svg";
import mongoIcon from "@/assets/svg/mongo.svg";
import defaultDbIcon from "@/assets/svg/db.svg";
import { useServices } from "../../EditSegmentedTemplate/service.ts";
interface IModalProps {
  initdata?: {
    db?: any;
    table?: string;
    field?: string;
  };
  relatedFields?: IRelatedFields[];
  isModalOpen: boolean;
  onFinish: (relations: any[]) => void;
  onClose: () => void;
}
interface IOptions {
  label: string;
  value: string;
}
interface IRelatedFields {
  fieldId?: string | number;
  tableId?: string | number;
  dbId?: string | number;
  fieldName?: string;
  tableName?: string;
  dbName?: string;
}

const dbIcon: any = {
  0: mysqlIcon,
  1: mongoIcon
};

const RelatedRelationshipModal = ({
  isModalOpen,
  initdata,
  relatedFields = [],
  onFinish,
  onClose
}: IModalProps) => {
  const [relatedFieldList, setRelatedFieldList] = useState<IRelatedFields[]>(
    []
  );
  const [fieldOptions, setFieldOptions] = useState<IOptions[][]>([]);
  const { getTableTree, getTableDetail } = useServices();
  const [tableTree, setTableTree] = useState<any[]>([]);

  useEffect(() => {
    if (isModalOpen) {
      getTableTreeData();
      if (relatedFields?.length > 0) {
        setRelatedFieldList(relatedFields);
      } else {
        addRow();
      }
    }
  }, [isModalOpen]);

  const getTableTreeData = async () => {
    const treeData = await getTableTree();
    // 获取树
    setTableTree(treeData);
  };

  const onConfirm = () => {
    console.log("-----relatedFieldList", relatedFieldList);

    onFinish && onFinish(relatedFieldList);
  };

  const isValidField = useMemo(() => {
    return relatedFieldList.every((rl) => rl.fieldId);
  }, [relatedFieldList]);

  const closeModal = () => {
    setRelatedFieldList([]);
    setFieldOptions([]);
    onClose && onClose();
  };
  const addRow = () => {
    setRelatedFieldList((pre: IRelatedFields[]) => {
      return [
        ...pre,
        {
          dbName: initdata?.db.name,
          dbId: initdata?.db.id
        }
      ];
    });
  };
  const onRemove = (index: number) => {
    setRelatedFieldList((pre: IRelatedFields[]) => {
      pre.splice(index, 1);
      return [...pre];
    });
  };
  const handleDbChange = (value: any, index: number) => {
    setRelatedFieldList((pre: IRelatedFields[]) => {
      pre[index] = {
        dbName: value.label,
        dbId: value.value
      };
      return [...pre];
    });
  };

  const handleTbChange = async (
    value: any,
    field: IRelatedFields,
    index: number
  ) => {
    setRelatedFieldList((pre: IRelatedFields[]) => {
      pre[index] = {
        dbName: field.dbName,
        dbId: field.dbId,
        tableName: value.label,
        tableId: value.value
      };
      return [...pre];
    });
    // 调用查询表字段接口
    const res = await getTableDetail(value.value);
    setFieldOptions((pre) => {
      pre[index] = res.fields;
      return [...pre];
    });
  };

  const handleFieldChange = (
    value: any,
    field: IRelatedFields,
    index: number
  ) => {
    setRelatedFieldList((pre: IRelatedFields[]) => {
      pre[index] = {
        ...field,
        fieldName: value.label,
        fieldId: value.value
      };
      return [...pre];
    });
  };

  return (
    <Modal
      title="配置关联关系"
      width={862}
      height={600}
      open={isModalOpen}
      onCancel={closeModal}
      footer={null}
    >
      <div className="h-[400px]">
        <div className="h-[44px] w-[794px] leading-[44px] bg-[#EAF4FF] px-[12px] rounded-[4px] my-[16px]">
          <label className="text-[#555555]">
            数据库:{" "}
            <span className="ml-[8px] text-[#2A2A2A]">
              {initdata?.db?.name || "-"}
            </span>
          </label>
          <label className="ml-[24px] text-[#555555]">
            数据表:{" "}
            <span className="ml-[8px] text-[#2A2A2A]">
              {initdata?.table || "-"}
            </span>
          </label>

          <label className="ml-[24px] text-[#555555]">
            字段名称:
            <span className="ml-[8px] text-[#2A2A2A]">
              {initdata?.field || "-"}
            </span>
          </label>
        </div>
        <div className="max-h-[300px] overflow-y-auto">
          {relatedFieldList.map((field, index) => {
            const tablesOption =
              tableTree.find((db) => db.id == field.dbId)?.tables || [];

            const fOptions = fieldOptions[index] ? fieldOptions[index] : [];

            return (
              <Space wrap key={index} className="my-[8px]">
                <Select
                  value={field.dbName}
                  style={{ width: 250 }}
                  labelInValue
                  onSelect={(value) => handleDbChange(value, index)}
                  placeholder="选择数据库"
                  // defaultValue={initdata?.db.name}
                  options={tableTree.map((db) => ({
                    label: db.name,
                    value: db.id,
                    desc: db.description,
                    type: db.type
                  }))}
                  optionRender={(option) => (
                    <Space className="flex flex-row my-[4px]">
                      <img
                        src={dbIcon[option.data.type] || defaultDbIcon}
                        width={28}
                        className="mt-[4px]"
                      />
                      <div className="flex flex-col">
                        <span className="font-medium">{option.data.label}</span>
                        <span className="text-[12px] text-[#888]">
                          描述：{option.data.desc || "-"}
                        </span>
                      </div>
                    </Space>
                  )}
                />
                <Select
                  style={{ width: 250 }}
                  placeholder="选择数据表"
                  value={field.tableName}
                  labelInValue
                  onSelect={(value) => handleTbChange(value, field, index)}
                  options={tablesOption.map((tb) => ({
                    label: tb.name,
                    value: tb.id
                  }))}
                />
                <Select
                  style={{ width: 250 }}
                  placeholder="选择字段"
                  value={field.fieldName}
                  labelInValue
                  onSelect={(value) => handleFieldChange(value, field, index)}
                  options={fOptions.map((f: any) => ({
                    label: f.name,
                    value: f.id
                  }))}
                />
                <DeleteOutlined
                  style={{ color: "#888888" }}
                  onClick={() => onRemove(index)}
                />
              </Space>
            );
          })}
        </div>
        <Button
          size="small"
          className="text-text-color2 border-[#EEEEEE] mt-[20px]  w-[70px] h-[24px]"
          icon={
            <img
              src={plusBlue}
              className="w-[14px] h-[14px] mr-[-4px] mt-[2px]"
            />
          }
          onClick={addRow}
        >
          添加
        </Button>
      </div>

      <div className="w-full mt-[20px] flex flex-row justify-end align-center">
        <Button
          type="primary"
          onClick={closeModal}
          style={{
            color: `#555555`,
            backgroundColor: "#fff",
            borderRadius: "4px",
            border: "1px solid #dedede"
          }}
        >
          取消
        </Button>
        <Button
          ghost
          onClick={onConfirm}
          disabled={!isValidField}
          style={{
            background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
            color: "#fff",
            opacity: !isValidField ? "50%" : "100%",
            border: "none",
            marginLeft: "10px"
          }}
        >
          确认
        </Button>
      </div>
    </Modal>
  );
};

export default RelatedRelationshipModal;
