import { Button, Form, Input, Table, Popconfirm, message, Flex } from "antd";
import {
  useEffect,
  useState,
  useMemo,
  forwardRef,
  useImperativeHandle
} from "react";
import { useTServices } from "./common/useTServices";
import { uid } from "uid";
import useAddTemplate from "./common/useAddTemplate";
import "./common/style.less";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { InitCount, TypeOptions, InitData } from "./common/constant";
import { useServices } from "../TemplateM/common/useServices";
import IconArrowLeft from "@/assets/svg/icon-arrow-left.svg";

interface DataType {
  key: number | string;
  dataIndex: string;
  title: string;
  required: boolean;
  type: string;
}
interface ICheckedData {
  id: string;
  name: string;
  isDelete?: boolean;
}

type EditableTableProps = Parameters<typeof Table>[0];
type ColumnTypes = Exclude<EditableTableProps["columns"], undefined>;

const EditTemplate = forwardRef((props: any, ref) => {
  const { isSegment = false, isOnceIn = true, onNext, templateId } = props;
  const navigator = useNavigate();
  const [form] = Form.useForm();
  const [name, setName] = useState("");
  const [sceneClass, setSceneClass] = useState([]);
  const [sceneKey, setSceneKey] = useState("");
  const [sceneClassTag, setSceneClassTag] = useState("");
  const [sensitiveWords, setSensitiveWords] = useState<ICheckedData[]>([]);

  const location = useLocation();
  const isVersion = useMemo(() => {
    return location.pathname.includes("/docWriting/template/version");
  }, [location]);

  const { createArticleType, updateArticleType, getSceneClass } = useTServices(
    {}
  );

  const { id, version } = useParams();
  const versionId = useMemo(() => {
    return version ? version.split("-")[0] : "";
  }, [version]);
  const versionTxt = useMemo(() => {
    return version ? version.split("-")[1] : 0;
  }, [version]);

  const modalType = id && id.indexOf("temp") > -1 ? "add" : "edit";
  const [dataSource, setDataSource] = useState<DataType[]>([InitData]);
  const [editData, setEditData] = useState<any>({});
  const { queryTemplateById, getVersionInfoById }: any = useServices({});
  const defaultColumns: (ColumnTypes[number] & {
    editable?: boolean;
    dataIndex: string;
  })[] = [
    {
      title: "变量",
      dataIndex: "dataIndex",
      width: 200,
      editable: true
    },
    {
      title: "显示名称",
      dataIndex: "title",
      width: 150,
      editable: true
    },
    {
      title: "类型",
      dataIndex: "type",
      editable: true,
      width: 150,
      render: (_, record) => {
        return TypeOptions.filter((item) => item.value === _).map(
          (v) => v.label
        );
      }
    },
    {
      title: "默认参数",
      dataIndex: "defaultValue",
      editable: true
    },
    {
      title: "必填项",
      dataIndex: "required",
      editable: true,
      width: 130,
      render: (_, record) => {
        return _ ? "是" : "否";
      }
    },

    {
      title: "操作",
      dataIndex: "operation",
      render: (_, record: any) =>
        dataSource.length >= 1 ? (
          <Popconfirm
            title="确定删除？"
            onConfirm={() => handleDelete(record.key)}
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
          >
            <Button type="link" disabled={record.key === InitCount}>
              删除
            </Button>
          </Popconfirm>
        ) : null
    }
  ];

  const extractFieldsFromString = (str: string) => {
    const regex = /\{\{([^{}]+)\}\}/g;
    const matches = str.match(regex);

    if (matches) {
      return matches.map((match) => match.replace(/{{(.*?)}}/g, "$1"));
    } else {
      return [];
    }
  };
  useEffect(() => {
    if ((id && id.indexOf("temp") == -1) || templateId) {
      const iid = templateId || id;

      if (!isVersion) {
        getTemplateById(iid);
      } else {
        if (String(versionId)) {
          getTemplateById(iid);
        }
      }
    }
    getSceneClassList();
    return () => {
      close();
    };
  }, [id, templateId, isVersion, versionId]);

  const getSceneClassList = async () => {
    const res = await getSceneClass.mutateAsync();
    if (res) {
      setSceneClass(res?.details || []);
    }
  };

  const getTemplateById = async (id: number | string) => {
    try {
      const res = isVersion
        ? await getVersionInfoById.mutateAsync({
            id,
            versionId
          })
        : await queryTemplateById.mutateAsync(id);

      // const res = await queryTemplateById.mutateAsync(id);
      if (res) {
        setEditData(res);
        const {
          paramsSchema,
          name,
          articleTypeKey,
          className,
          promptTemplateUser,
          promptTemplateSystem,
          supportMaterials,
          supportOutlines,
          traceToMaterial,
          contentRule,
          sensitiveWords
        } = res;
        const prompt = isSegment
          ? promptTemplateSystem || ""
          : promptTemplateUser;
        try {
          form.setFieldsValue({ name });
          setName(name);
          setPrompt(prompt);
          setConentRule(contentRule || "");
          setSceneKey(articleTypeKey);
          setSceneClassTag(className);
          const tableData = JSON.parse(paramsSchema);
          setTableList(tableData.uiSchema);
          setSupportMaterials(supportMaterials == 1 ? true : false);
          setSupportOutlines(supportOutlines == 1 ? true : false);
          setTraceToMaterial(traceToMaterial == 1 ? true : false);
          const sw: ICheckedData[] = Object.entries(sensitiveWords).map(
            ([id, name]) => ({
              id: Number(id), // 如果key需要是数字类型
              name
            })
          );
          setSensitiveWords(sw);
        } catch (e) {
          console.log("e----->", e);
        }
      }
    } catch (e) {
      console.log("e", e);
    }
  };
  const valuesExistInArray = (arr1: any[], arr2: any[]) => {
    return arr1.every((value) => {
      const res = arr2.includes(value);
      if (!res) {
        message.warning(`系统提示词${value}未配置参数`);
      }
      return res;
    });
  };

  const judgeDataSource = (data: any[], promptTemplateUser: string) => {
    let isValid = true,
      isTemplate = true;

    const tableNames: any[] = [];

    for (let index = 0; index < data.length; index++) {
      const item = data[index];
      // 校验参数名称重复
      if (tableNames.includes(item.dataIndex)) {
        message.warning(`参数名称 "${item.dataIndex}" 不可重复`);
        return false;
      }
      tableNames.push(item.dataIndex);
      // 校验是否有字段值为空
      const hasEmptyValues = Object.keys(item).some((key) => {
        const value = item[key];
        // type为select, defaultValue不能为null或空字符串或undefined, type不为select,defaultValue不校验
        if (key == "type" && value == "select") {
          if (!item?.defaultValue || item.defaultValue?.length <= 0) {
            return true;
          }
        } else {
          if (key !== "defaultValue") {
            // 除defaultValue以外的所有value值，不能为null或空字符串或undefined
            return value === "" || value === null || value === undefined;
          }
        }
      });
      // 有字段为空。弹提示
      if (hasEmptyValues) {
        isValid = false;
        for (const [key, value] of Object.entries(item)) {
          if (value === "" || value === null || value === undefined) {
            message.warning(
              `第 ${index + 1} 行的 "${defaultColumns
                .filter((item) => item.dataIndex === key)
                .map((v) => v.title)}" 字段值为空`
            );
            return;
          }
          // type select默认值必填
          if (
            item.type == "select" &&
            (!item?.defaultValue || item.defaultValue?.length <= 0)
          ) {
            message.warning(
              `第 ${index + 1} 行type为 'select'时 "defaultValue" 字段不能为空`
            );
            return;
          }
        }
      }
    }

    if (!isValid) {
      return isValid;
    }

    // 场景全文配置中，需要校验table里是否设置了所有系统提示词
    if (!isSegment) {
      const temps = extractFieldsFromString(promptTemplateUser);

      isTemplate = valuesExistInArray(temps, tableNames);

      if (!isTemplate) {
        return isTemplate;
      }
    }

    return true;
  };

  const handleDelete = (key: React.Key) => {
    const newData = dataSource.filter((item) => item.key !== key);
    setDataSource(newData);
  };

  const onFinish = async (next?: boolean) => {
    if (isVersion) {
      onNext(null, next);
      return;
    }
    form
      .validateFields()
      .then(async (data) => {
        const promptTemplate = getPromptTemplate();
        if (!promptTemplate) {
          return message.warning("请填写系统提示词!");
        }
        const isValid = judgeDataSource(formSchema, promptTemplate);
        const params = {
          ...data,

          paramsSchema: JSON.stringify({
            uiSchema: formSchema,
            $id: uid(),
            title: data.name,
            properties: {},
            required: [],
            description: "",
            type: ""
          }),
          generateType: isSegment ? 1 : 0,
          contentRule: getContentRule(),
          className: selectTag,
          articleTypeKey,
          sensitiveWords: checkedData
            .filter((item) => !item?.isDelete)
            .reduce((acc, item) => {
              acc[item.id] = item.name;
              return acc;
            }, {}),
          supportMaterials: supportMaterials ? 1 : 0,
          supportOutlines: supportOutlines ? 1 : 0,
          traceToMaterial: traceToMaterial ? 1 : 0,
          formatTemplate: editData?.formatTemplate
            ? editData?.formatTemplate
            : undefined
        };
        if (isSegment) {
          params.promptTemplateSystem = promptTemplate;
        } else {
          params.promptTemplateUser = promptTemplate;
        }
        if (isValid) {
          let res: any;
          if (modalType == "edit" || templateId) {
            params.id = editData.id;
            if (isSegment && isOnceIn && !isOnceIn.current) {
              // 不是第一次进来,不需要升级版本
              // 如果点击敏感词库,不需要升级版本
              params.versionId = editData.versionId;
            }
            res = await updateArticleType.mutateAsync(params);
          } else {
            res = await createArticleType.mutateAsync(params);
          }
          if (res?.success) {
            if (isSegment) {
              onNext(res.data, next);
            } else {
              if (modalType == "edit") {
                message.success("模板保存成功");
              } else {
                message.success("新建模板成功");
              }
              navigator("/docWriting/template");
            }
          }
        }
        return null;
      })
      .catch((e) => {
        console.log("e------->", e);
      });
  };

  const {
    WidgetElement,
    getPromptTemplate,
    getContentRule,
    setConentRule,
    formSchema,
    selectTag,
    articleTypeKey,
    setPrompt,
    setTableList,
    supportMaterials,
    setSupportMaterials,
    supportOutlines,
    setSupportOutlines,
    traceToMaterial,
    setTraceToMaterial,
    checkedData,
    close
  } = useAddTemplate(
    name,
    sceneClass,
    sceneKey,
    sceneClassTag,
    isSegment,
    sensitiveWords,
    isVersion
  );

  const goBack = (key: number) => () => {
    navigator(key);
  };

  useImperativeHandle(ref, () => ({
    onFinish
  }));

  return (
    <div
      className={`${isSegment ? "h-full" : "h-[calc(100%-20px)] rounded-lg"} overflow-hidden bg-transparent`}
    >
      {!isSegment && (
        <Flex justify="flex-start" align="center" className="mb-4">
          <img
            className="mr-2 pb-[2px] cursor-pointer"
            src={IconArrowLeft}
            onClick={goBack(-1)}
          />
          <b className="text-base text-text-color1">
            {isVersion
              ? `查看场景版本 - V1.${versionTxt}`
              : modalType === "edit"
                ? "编辑场景"
                : "新建场景"}
          </b>
        </Flex>
      )}
      <div
        className={`${isSegment ? "" : "rounded-lg"} h-full relative overflow-x-hidden overflow-y-auto bg-white`}
      >
        {!isSegment ? (
          <div className="flex justify-end bg-white absolute z-50 bottom-10 right-0 left-0 pr-3 rounded-lg rounded-t-none h-10 pb-2 pt-1">
            <Button
              type="primary"
              onClick={() => {
                close();
                navigator(-1);
              }}
              style={{
                color: `#555555`,
                backgroundColor: "#fff",
                borderRadius: "4px",
                border: "1px solid #dedede"
              }}
            >
              取消
            </Button>
            {!isVersion ? (
              <Button
                ghost
                onClick={() => onFinish()}
                style={{
                  background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                  color: "#fff",
                  border: "none",
                  borderRadius: "4px",
                  marginLeft: "10px"
                }}
              >
                确认
              </Button>
            ) : null}
          </div>
        ) : null}
        <div
          className={`bg-white pt-5 px-5 rounded-lg ${isSegment ? "h-full" : "h-[calc(100%-40px)] pb-11"} overflow-y-auto overflow-x-hidden flex flex-col`}
        >
          <Form
            name="basic"
            initialValues={{ remember: true }}
            form={form}
            autoComplete="off"
            className="addTemplateForm"
            layout="vertical"
          >
            <Form.Item
              label="场景名称"
              name="name"
              rules={[{ required: true, message: "请输入场景名称!" }]}
            >
              <Input
                disabled={isVersion}
                onChange={(e) => {
                  setName(e.target.value);
                }}
              />
            </Form.Item>
          </Form>
          <div
            className={`w-full flex addTemplateForm ${isSegment ? "mb-4" : "mb-4"}`}
          >
            <div className="w-full">{WidgetElement}</div>
          </div>
        </div>
      </div>
    </div>
  );
});

export default EditTemplate;
