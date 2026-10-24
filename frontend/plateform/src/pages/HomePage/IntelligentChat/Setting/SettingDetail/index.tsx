import {
  Button,
  Flex,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Slider,
  Switch,
  Tooltip,
  message
} from "antd";
import TextArea from "antd/es/input/TextArea";
import axios$ from "@root/src/apis";
import { useEffect, useMemo, useState } from "react";
import { HomeOutlined, QuestionCircleOutlined } from "@ant-design/icons";
import { useNavigate, useParams } from "react-router-dom";
import {
  EXPLANATION_MAXTOKENS,
  EXPLANATION_TEMPERATURE,
  EXPLANATION_TOP_P,
  EXPLANATION_PROMPT,
  EXPLANATION_TOP_K,
  EXPLANATION_SIMILAR_THRESHOLD,
  EXPLANATION_MAX_ROUND,
  EXPLANATION_DEPENDON_KB
} from "@root/src/const";
import { getLibraryList } from "../../SensitiveWords/common/sensiveService";
import "./style.less";
import SelectBox from "../SelectBox";
import useSystemApi from "@root/src/apis/system";
import _ from "lodash";
import { ASSISTANT_MIN_MAX } from "../Constant";
import { getUrlPrefix } from "@root/src/core/helps";
import { useSelector } from "react-redux";
const DEFAULT_PROMPT =
  '你是一个智能助手，请总结知识库的内容来回答问题,请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括"知识库中未找到您要的答案!"';
const DEFAULT_ANSWER =
  "您好！我注意到您的消息中可能包含了一些敏感的内容。为了保证社区的友好氛围，我们无法继续就此话题进行讨论。如果您有其他问题或需要帮助，我很乐意继续为您服务！谢谢您的理解和支持。";
const TOP_P = 0.8;
const SCORE_THRESHOLD = 0.1;
const TOP_K = 10;
const TEMPERATURE = 0.3;

const NotFoundContent = () => {
  return (
    <div className="w-full h-[80px] rounded-md flex flex-col justify-center items-center">
      <svg
        width="64"
        height="41"
        viewBox="0 0 64 41"
        xmlns="http://www.w3.org/2000/svg"
      >
        <g transform="translate(0 1)" fill="none" fill-rule="evenodd">
          <ellipse fill="#f5f5f5" cx="32" cy="33" rx="32" ry="7"></ellipse>
          <g fill-rule="nonzero" stroke="#d9d9d9">
            <path d="M55 12.76L44.854 1.258C44.367.474 43.656 0 42.907 0H21.093c-.749 0-1.46.474-1.947 1.257L9 12.761V22h46v-9.24z"></path>
            <path
              d="M41.613 15.931c0-1.605.994-2.93 2.227-2.931H55v18.137C55 33.26 53.68 35 52.05 35h-40.1C10.32 35 9 33.259 9 31.137V13h11.16c1.233 0 2.227 1.323 2.227 2.928v.022c0 1.605 1.005 2.901 2.237 2.901h14.752c1.232 0 2.237-1.308 2.237-2.913v-.007z"
              fill="#fafafa"
            ></path>
          </g>
        </g>
      </svg>
      <div>暂无可用模型</div>
    </div>
  );
};
const SettingDetail = (props: any) => {
  const api = useSystemApi();
  const {
    drawConfig,
    btnLoading,
    openDraw,
    knowledgeBaseOption,
    curMenuKey,
    knowledgeShareBaseOption
  } = props;
  const [form] = Form.useForm();
  const [isModalShow, setIsModalShow] = useState(false);
  const [modelList, setModelList]: any = useState();
  const [model, setModel] = useState("");

  // bind local variables
  const [temperature, setTemperature] = useState(TEMPERATURE);
  const [diversity, setDiversity] = useState(TOP_P);
  const [recallChunksNum, setRecallChunkNum] = useState(
    ASSISTANT_MIN_MAX.top_k.default
  );
  const [similarThreshold, setSimilarThreshold] = useState(SCORE_THRESHOLD);
  const [maxToken, setMaxToken] = useState(
    ASSISTANT_MIN_MAX.max_tokens.default
  );
  const [maxRound, setMaxRound] = useState(ASSISTANT_MIN_MAX.max_round.default);
  const [sensitiveWordsOption, setSensitiveWordsOption] = useState([]);
  const [sensitiveWordIds, setSensitiveWordIds]: any = useState([]);
  const [knowledge_base_name_source, setKnowledge_base_name_source]: any =
    useState([]);
  const [isDefault, setIsDefault] = useState(false);
  const [show_similar_threshold, set_show_similar_threshold] = useState(true);
  const [set_FAQ_priority, set_set_FAQ_priority] = useState(false);
  const [enabled_graph, set_enabled_graph] = useState(false);
  const [dependOnKb, setDependOnKb] = useState(false);
  const [need_trace_source, set_need_trace_source] = useState(true);
  const [trace_by_llm, set_trace_by_llm] = useState(true);
  const [database_name, set_database_name] = useState<any>(
    ASSISTANT_MIN_MAX.database_name.default
  );

  const [is_download, set_is_download] = useState(false);
  const [enabled_question_rewrite, set_enabled_question_rewrite] =
    useState(false);
  const [search_policy, set_search_policy] = useState(1);
  const [configScale, setConfigScale] = useState(ASSISTANT_MIN_MAX);
  const [databaseOptions, setDatabaseOptions] = useState([]);

  const [rerankOptions, setRerankOptions] =
    useState<{ label: string; value: string }[]>();
  const [multiModelOptions, setMultiModalOptions] =
    useState<{ label: string; value: string }[]>();
  const globalMenu: any = useSelector((state: any) => state.global.globalMenu);

  const databasePermission = useMemo(() => {
    if (!globalMenu) return;
    //这里目前只处理写作模版的权限
    const docMenu = globalMenu.find((i: any) => i.url === "/chats/database");
    if (!docMenu) return false;
    return docMenu.permission;
  }, [globalMenu]);

  const fetchConfig = async () => {
    try {
      const response = await api.getConfigItemLimit();
      if (response?.data) {
        setConfigScale(response.data as any);
      }
    } catch (error) {
      console.error("获取配置失败:", error);
    }
  };
  const fetchModels = async () => {
    const systemApi = useSystemApi({ baseURL: getUrlPrefix() });
    try {
      const [modelRes, recallModelRes, multiModelRes] =
        await Promise.allSettled([
          systemApi.getAllModelList({
            pageNum: 1,
            pageSize: 9999,
            status: 1,
            type: 1
          }),
          systemApi.getAllModelList({
            pageNum: 1,
            pageSize: 9999,
            status: 1,
            type: 3
          }),
          systemApi.getAllModelList({
            pageNum: 1,
            pageSize: 9999,
            status: 1,
            type: 4
          })
        ]);
      if (modelRes.status === "fulfilled" && modelRes.value) {
        const list = modelRes.value.data?.records || [];
        const options = list.map((item: any) => ({
          ...item,
          label: item.modelName,
          value: item.modelName
        }));
        setModelList(options);
      }

      if (recallModelRes.status === "fulfilled" && recallModelRes.value) {
        const options = (recallModelRes.value?.data?.records || []).map(
          (item: any) => ({
            label: item.modelName || item.name,
            value: item.modelName || item.name
          })
        );
        setRerankOptions(options);
        if (options.length > 0) {
          form.setFieldsValue({ recallModel: options[0].value });
        }
      }
      if (multiModelRes.status === "fulfilled" && multiModelRes.value) {
        const options = (multiModelRes.value?.data?.records || []).map(
          (item: any) => ({
            label: item.modelName || item.name,
            value: item.modelName || item.name
          })
        );
        setMultiModalOptions(options);
        if (options.length > 0) {
          form.setFieldsValue({ multi_model_name: options[0].value });
        }
      }
    } catch (e) {
      console.error("获取模型列表失败:", e);
    }
  };

  const fetchLibrary = async () => {
    try {
      const res = await getLibraryList({
        pageNo: 1,
        pageSize: 9999
      });
      if (res) {
        const { records } = res;

        setSensitiveWordsOption(
          records.map((item: any) => {
            return { ...item, id: item.id + "" };
          })
        );
      }
    } catch (e) {
      console.log("e", e);
    }
  };

  // index/database/queryAllDBList
  const fetchDatabases = async () => {
    try {
      const res: any = await axios$.get(
        `${getUrlPrefix()}/index/database/queryAllDBList`
      );
      const { success, data } = res;
      if (success) {
        setDatabaseOptions(
          data.map((item: any) => {
            return { ...item, id: item.primitiveName };
          })
        );
      }
      return false;
    } catch (e) {
      console.error("e", e);
    }
  };

  const clearForm = () => {
    setTemperature(TEMPERATURE);
    setDiversity(TOP_P);
    setRecallChunkNum(ASSISTANT_MIN_MAX.top_k.default);
    setSimilarThreshold(SCORE_THRESHOLD);
    setMaxToken(4096);
    setMaxRound(5);
    setSensitiveWordIds([]);
    setCustomReply(false);
    set_show_similar_threshold(true);
    set_set_FAQ_priority(false);
    set_database_name(ASSISTANT_MIN_MAX.database_name.default);
    set_enabled_graph(false);
    setDependOnKb(false);
    setIsDefault(false);
    setKnowledge_base_name_source_checkedData([]);
  };

  const handleUpdate = async () => {
    const formData = form.getFieldsValue();
    console.log("form data:", formData);

    try {
      await form.validateFields();
    } catch (e) {
      console.log("Form validate failed", e);
      return;
    }
    const config_name = form.getFieldValue("config_name");
    const duplicated_record = props.configNameList.find(
      (item: any) => item.name == config_name
    );
    if (drawConfig?.type === "create") {
      if (duplicated_record) {
        message.warning("名称重复！", 2);
        return;
      }
    } else {
      if (duplicated_record && duplicated_record.id != drawConfig?.data?.key) {
        message.warning("名称重复！", 2);
        return;
      }
    }

    // bugfix begin
    // model_name之前的数据传错为label，此处检测，如果是错误数据，则修改成value
    // 20241022
    const _modelName = form.getFieldValue("model_name");
    const _model = (modelList || []).find(
      (i: any) => i.label === _modelName
    ) as any;
    if (_model && _model.value && _model.value !== _modelName) {
      form.setFieldValue("model_name", _model.value);
    }
    // bugfix end

    // format prompt field

    // 将模型里的是否支持推理字段带到助手配置中
    formData.thinking =
      (modelList.find((item: any) => item.modelName == _modelName) as any)
        ?.thinking || false;

    const prompt0 = form
      .getFieldValue("system_prompt")
      ?.replace(/\n/g, "")
      ?.replace(/\s/g, "");
    form.setFieldValue("system_prompt", prompt0 || "");

    if (drawConfig?.data && !formData.defaultAnswer) {
      drawConfig.data["defaultAnswer"] = DEFAULT_ANSWER;
    }

    const kbNS = _.cloneDeep(formData.knowledge_base_name_source);

    formData.knowledge_base_name_source = kbNS
      .map((i: any) => i.knowledge_base_name_source)
      .join(";");
    formData.knowledge_base_name = kbNS
      .map((i: any) => i.knowledge_base_name)
      .join(";");
    formData.selectedKnowledgeBase = kbNS
      .filter((item: any) => {
        return item.labels?.length;
      })
      .map((item: any) => {
        return {
          id: item.kbId,
          name: item.knowledge_base_name,
          labels: item.labels,
          knowledge_base_name_source: item.name
        };
      });
    let databaseList = databaseOptions
      .filter((item: any) =>
        (formData?.database_name_source || []).includes(item.id)
      )
      .map((item: any) => {
        return {
          label: item.name,
          key: item.id
        };
      });

    if (drawConfig.type == "create") {
      const p1 = {
        ...formData,
        isDefault,
        show_similar_threshold,
        set_FAQ_priority,
        enabled_graph,
        dependOnKb,
        need_trace_source,
        trace_by_llm,
        is_download,
        search_policy,
        enabled_question_rewrite,
        database_name: databaseList || ASSISTANT_MIN_MAX.database_name.default
      };
      props.onCreate && props.onCreate(p1);
    } else if (drawConfig.type == "edit") {
      const p2 = {
        ...drawConfig?.data,
        ...formData,
        isDefault,
        show_similar_threshold,
        set_FAQ_priority,
        enabled_graph,
        dependOnKb,
        need_trace_source,
        trace_by_llm,
        is_download,
        search_policy,
        enabled_question_rewrite,
        database_name: databaseList || ASSISTANT_MIN_MAX.database_name.default
      };
      props.onUpdate && props.onUpdate(p2);
    }
  };
  const handleChage = (key: string, value: any) => {
    form.setFieldValue(key, value);
  };

  const checkConfigName = () => {
    const config_name = form.getFieldValue("config_name");
    const duplicated_record = props.configNameList.find(
      (item: any) => item.name == config_name
    );
    if (
      duplicated_record != undefined &&
      duplicated_record.id != drawConfig?.data.key
    ) {
      message.warning("名称重复！", 2);
    }
  };

  const handleDelete = () => {
    props.onDelete && props.onDelete(drawConfig?.data.key);
  };

  const [customReply, setCustomReply] = useState(false);
  const [checkedData, setCheckedData] = useState<string[]>([]);
  const [
    knowledge_base_name_source_checkedData,
    setKnowledge_base_name_source_checkedData
  ] = useState<string[]>([]);
  const [database_source_checkData, setDatabase_source_checkData] = useState<
    string[]
  >([]);

  const handleChange = (key: string, value: any) => {
    form.setFieldValue(key, value);
  };

  useEffect(() => {
    fetchLibrary();
    fetchConfig();
    //fetchDatabases();
    fetchModels();
  }, []);

  useEffect(() => {
    handleChange("sensitiveWordIds", checkedData);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [checkedData]);

  useEffect(() => {
    handleChange(
      "knowledge_base_name_source",
      knowledge_base_name_source_checkedData
    );
  }, [knowledge_base_name_source_checkedData]);

  useEffect(() => {
    handleChage("database_name_source", database_source_checkData);
  }, [database_source_checkData]);

  useEffect(() => {
    if (drawConfig.type !== "edit" && drawConfig.type !== "view") {
      setTimeout(() => {
        setKnowledge_base_name_source_checkedData([]);
      }, 1000);
    }
  }, [drawConfig.type]);

  const DEFAULT_RERANK = useMemo(() => {
    return Array.isArray(rerankOptions) && rerankOptions[0]?.value;
  }, [rerankOptions]);

  useEffect(() => {
    if (
      drawConfig?.data &&
      (drawConfig.type == "edit" || drawConfig.type == "view")
    ) {
      form.setFieldsValue({
        prologue: drawConfig?.data.prologue || "",
        config_name: drawConfig?.data.config_name,
        description: drawConfig?.data.des,
        system_prompt: drawConfig?.data.prompt
          ? drawConfig?.data.prompt
          : drawConfig?.data.system_prompt, // field name changed, reserve previous data,show_similar_threshold,set_FAQ_priority
        model_name: drawConfig?.data.model_name,
        rerank_model_name: drawConfig.data.rerank_model_name || DEFAULT_RERANK,
        sensitiveWordIds: drawConfig?.data.sensitiveWordIds,
        defaultAnswer: drawConfig?.data.defaultAnswer || DEFAULT_ANSWER,
        max_tokens: drawConfig?.data.max_tokens,
        max_round: drawConfig?.data.max_round,
        knowledge_base_name_source: Array.isArray(
          drawConfig?.data?.knowledge_base_name_source
        )
          ? drawConfig?.data?.knowledge_base_name_source
          : drawConfig?.data?.knowledge_base_name_source?.split(";"),
        score_threshold: drawConfig?.data.score_threshold,
        top_k: drawConfig?.data.top_k,
        temperature: drawConfig?.data.temperature,
        top_p: drawConfig?.data?.top_p || drawConfig?.data?.similar_threshold,
        trace_by_llm: drawConfig?.data?.trace_by_llm,
        search_policy: drawConfig?.data?.search_policy,
        recommend_model_name: drawConfig?.data?.recommend_model_name,
        plan_model_name: drawConfig?.data?.plan_model_name
      });
      setModel(drawConfig?.data.model_name);
      set_trace_by_llm(drawConfig?.data?.trace_by_llm || false);
      setSensitiveWordIds(
        Array.isArray(drawConfig?.data?.sensitiveWordIds)
          ? drawConfig?.data?.sensitiveWordIds
          : drawConfig?.data?.sensitiveWordIds
          ? drawConfig?.data?.sensitiveWordIds?.split(",")
          : []
      );
      setTemperature(drawConfig?.data?.temperature);
      setDiversity(
        drawConfig?.data?.top_p || drawConfig?.data?.similar_threshold
      );
      setRecallChunkNum(drawConfig?.data?.top_k);
      setSimilarThreshold(drawConfig?.data?.score_threshold);
      setMaxToken(drawConfig?.data?.max_tokens);
      setMaxRound(drawConfig?.data?.max_round);
      setIsDefault(drawConfig?.data?.isDefault ? true : false);
      set_show_similar_threshold(drawConfig?.data?.enabled_rerank);
      set_set_FAQ_priority(drawConfig?.data?.enabled_faq);

      set_enabled_graph(drawConfig?.data?.enabled_graph);

      const databseIds = (
        Array.isArray(drawConfig.data.database_name)
          ? drawConfig?.data?.database_name
          : []
      ).map((d: { key: string; label: string }) => d.key);
      set_database_name(databseIds || ASSISTANT_MIN_MAX.database_name.default);

      setDependOnKb(!!drawConfig?.data?.dependOnKb);
      set_need_trace_source(!!drawConfig?.data?.need_trace_source);
      set_is_download(!!drawConfig?.data?.is_download);
      set_enabled_question_rewrite(
        !!drawConfig?.data?.enabled_question_rewrite
      );
      set_trace_by_llm(!!drawConfig?.data?.trace_by_llm);
      set_search_policy(drawConfig?.data?.search_policy);

      if (
        drawConfig?.data?.sensitiveWordIds?.length &&
        drawConfig?.data?.defaultAnswer !== DEFAULT_ANSWER
      ) {
        setCustomReply(true);
      } else {
        setCustomReply(false);
      }
    } else {
      form.resetFields();
      clearForm();
    }
  }, [drawConfig, form, openDraw]);

  useEffect(() => {
    // 单独处理需要接口返回数据作为依赖项的state, 防止其余state重复刷新
    if (
      drawConfig?.data &&
      (drawConfig.type == "edit" || drawConfig.type == "view")
    ) {
      const selectedKnowledgeBase = drawConfig?.data?.selectedKnowledgeBase;
      const kMap = new Map();
      if (selectedKnowledgeBase?.length) {
        selectedKnowledgeBase.forEach((item: any) => {
          const id = item.knowledge_base_name_source;
          if (!kMap.has(id)) {
            kMap.set(id, {
              kbId: item.id,
              name: item.knowledge_base_name_source,
              knowledge_base_name: item.name,
              knowledge_base_name_source: item.knowledge_base_name_source,
              labels: item.labels,
              id: item.knowledge_base_name_source
            });
          }
        });
      }
      const knowledge_base_name_source =
        drawConfig?.data?.knowledge_base_name_source;
      const Knowledge_base_name_source_arr = Array.isArray(
        knowledge_base_name_source
      )
        ? knowledge_base_name_source
        : knowledge_base_name_source
        ? knowledge_base_name_source.split(";")
        : [];
      const _list = Knowledge_base_name_source_arr.map((n: string) => {
        if (kMap.has(n)) {
          return kMap.get(n);
        }
        return (
          (
            (curMenuKey === "1"
              ? knowledgeBaseOption
              : knowledgeShareBaseOption) || []
          ).find((i: any) => i.name === n) || []
        );
      });
      setKnowledge_base_name_source(_list);
    }
    if (drawConfig.type == "edit") {
      //编辑的话，只有模型列表返回为空才需要校验
      if (Array.isArray(modelList) && Array.isArray(rerankOptions)) {
        form.validateFields([
          "model_name",
          "plan_model_name",
          "recommend_model_name",
          "rerank_model_name",
          "multi_model_name"
        ]);
      }
      if (Array.isArray(multiModelOptions)) {
        form.validateFields(["multi_model_name"]);
      }
    } else if (drawConfig.type == "create") {
      //新增的话，只有模型列表返回为空才需要校验
      if (Array.isArray(modelList) && modelList?.length == 0) {
        form.validateFields([
          "model_name",
          "plan_model_name",
          "recommend_model_name"
        ]);
      }

      if (Array.isArray(rerankOptions) && rerankOptions?.length == 0) {
        form.validateFields(["rerank_model_name"]);
      }
      if (Array.isArray(multiModelOptions) && multiModelOptions?.length == 0) {
        form.validateFields(["multi_model_name"]);
      }
    }
  }, [
    openDraw,
    drawConfig,
    rerankOptions,
    knowledgeBaseOption,
    knowledgeShareBaseOption,
    modelList,
    rerankOptions,
    multiModelOptions,
    form,
    modelList
  ]);

  useEffect(() => {
    if (!openDraw) {
      const scrollBox = document.getElementById("formId");
      scrollBox &&
        scrollBox.scrollTo({
          top: 0
        });
    }
  }, [openDraw]);

  const validateNumber = (min: number, max: number) => ({
    validator(_: any, value: any) {
      // 自定义验证逻辑
      if (value === null || value === undefined) {
        return Promise.reject("请输入有效数字");
      }
      if (typeof +value !== "number" || isNaN(+value)) {
        return Promise.reject("只能输入数字");
      }
      if (value < min || value > max) {
        return Promise.reject(`请输入${min}到${max}之间的数字`);
      }
      return Promise.resolve();
    }
  });

  return (
    <Flex
      style={{
        backgroundColor: "#fff",
        borderRadius: "4px",
        flexDirection: "column",
        height: "100%"
      }}
      className="settingsDetail"
    >
      <Flex
        justify="center"
        id="formId"
        className=" h-[calc(100%-85px)] overflow-auto bg-gradient-to-br from-white to-gray-50 rounded-lg shadow-md"
      >
        <Form
          form={form}
          wrapperCol={{ span: 24 }}
          style={{
            display: "flex",
            flexDirection: "column",
            minWidth: "700px",
            background: "#fff",
            borderRadius: 12,
            boxShadow: "0 2px 16px 0 #f3f6fa",
            padding: 32,
            marginBottom: 24
          }}
          layout="vertical"
          initialValues={{
            temperature: TEMPERATURE,
            score_threshold: SCORE_THRESHOLD,
            top_k: ASSISTANT_MIN_MAX.top_k.default,
            top_p: TOP_P,
            max_tokens: 4096,
            max_round: 5,
            defaultAnswer: DEFAULT_ANSWER,
            system_prompt: "" //DEFAULT_PROMPT,
          }}
          disabled={drawConfig?.type === "view"}
        >
          {/* 基础信息分组 */}
          <div className="mb-8">
            <div
              className="text-lg font-bold text-primary-color mb-4 border-l-4
             border-blue-200 pl-3 bg-blue-50/40 rounded"
            >
              基础信息
            </div>
            <Flex gap={20}>
              <Form.Item
                name="config_name"
                label={
                  <span className="font-semibold text-gray-900">
                    会话助手名称
                  </span>
                }
                style={{ flex: "1" }}
                rules={[{ required: true, message: "请输入会话助手名称" }]}
              >
                <Input
                  onBlur={checkConfigName}
                  className="w-[356px] rounded-lg"
                  placeholder="请输入"
                />
              </Form.Item>
              <Form.Item
                name="model_name"
                shouldUpdate
                label={
                  <span className="font-semibold text-gray-900">问答模型</span>
                }
                style={{ flex: "1" }}
                validateTrigger="onChange"
                rules={[
                  {
                    required: true,
                    validator(_: any, value: any) {
                      const options = modelList || [];
                      if (!value) {
                        if (Array.isArray(options) && options.length === 0) {
                          return Promise.reject("暂无可用模型，请联系管理员");
                        } else {
                          return Promise.reject("请选择问答模型");
                        }
                      }
                      if (
                        (Array.isArray(options) && options.length === 0) ||
                        !options.find((m: any) => m.value == value)
                      ) {
                        return Promise.reject("模型无法使用，请联系管理员");
                      }
                      return Promise.resolve();
                    }
                  }
                ]}
              >
                <Select
                  options={modelList}
                  className="w-[356px] rounded-lg"
                  placeholder="请选择"
                  value={model}
                  notFoundContent={<NotFoundContent />}
                  onChange={(value) => {
                    setModel(value);
                    form.setFieldValue("model_name", value);
                  }}
                ></Select>
              </Form.Item>
            </Flex>
            <Form.Item
              name="plan_model_name"
              label={
                <span className="font-semibold text-gray-900">规划模型</span>
              }
              rules={[
                {
                  required: true,
                  validator(_: any, value: any) {
                    const options = modelList || [];
                    if (!value) {
                      if (Array.isArray(options) && options.length === 0) {
                        return Promise.reject("暂无可用模型，请联系管理员");
                      } else {
                        return Promise.reject("请选择规划模型");
                      }
                    }
                    if (
                      (Array.isArray(options) && options.length === 0) ||
                      !options.find((m: any) => m.value == value)
                    ) {
                      return Promise.reject("模型无法使用，请联系管理员");
                    }
                    return Promise.resolve();
                  }
                }
              ]}
            >
              <Select
                options={modelList}
                className="w-[356px] rounded-lg"
                placeholder="请选择"
                notFoundContent={<NotFoundContent />}
              ></Select>
            </Form.Item>
            <Form.Item
              name="multi_model_name"
              label={
                <span className="font-semibold text-gray-900">
                  上传文档问答多模态模型
                </span>
              }
              rules={[
                {
                  required: true,
                  validator(_: any, value: any) {
                    const options = multiModelOptions || [];
                    if (!value) {
                      if (Array.isArray(options) && options.length === 0) {
                        return Promise.reject("暂无可用模型，请联系管理员");
                      } else {
                        return Promise.reject(
                          "请选择上传文档问答多模态模型模型"
                        );
                      }
                    }
                    if (
                      (Array.isArray(options) && options.length === 0) ||
                      !options.find((m: any) => m.value == value)
                    ) {
                      return Promise.reject("模型无法使用，请联系管理员");
                    }
                    return Promise.resolve();
                  }
                }
              ]}
            >
              <Select
                options={multiModelOptions}
                className="w-[356px] rounded-lg"
                placeholder="请选择"
                notFoundContent={<NotFoundContent />}
              ></Select>
            </Form.Item>
            <Form.Item
              name="prologue"
              label={
                <span className="font-semibold text-gray-900">开场白</span>
              }
            >
              <Input placeholder="请输入开场白" className="rounded-lg" />
            </Form.Item>
            <Form.Item
              name="system_prompt"
              label={
                <span className="font-semibold text-gray-900">
                  提示词
                  <Tooltip title={EXPLANATION_PROMPT}>
                    <QuestionCircleOutlined
                      style={{ color: "#666", marginLeft: "5px" }}
                    />
                  </Tooltip>
                </span>
              }
            >
              <TextArea
                style={{ height: "100px", resize: "none" }}
                placeholder={`例如：${DEFAULT_PROMPT}`}
                className="rounded-lg"
              ></TextArea>
            </Form.Item>
          </div>
          {/* 检索与生成参数分组 */}
          <div className="mb-8">
            <div
              className="text-lg font-bold text-primary-color mb-4 border-l-4
             border-blue-200 pl-3 bg-blue-50/40 rounded"
            >
              检索与生成参数
            </div>
            <Form.Item
              name="recommend_model_name"
              label={
                <span className="font-semibold text-gray-900">问题推荐</span>
              }
              rules={[
                {
                  required: true,
                  validator(_: any, value: any) {
                    const options = modelList || [];
                    if (!value) {
                      if (Array.isArray(options) && options.length === 0) {
                        return Promise.reject("暂无可用模型，请联系管理员");
                      } else {
                        return Promise.reject("请选择问题推荐");
                      }
                    }
                    if (
                      (Array.isArray(options) && options.length === 0) ||
                      !options.find((m: any) => m.value == value)
                    ) {
                      return Promise.reject("模型无法使用，请联系管理员");
                    }
                    return Promise.resolve();
                  }
                }
              ]}
            >
              <Select
                options={modelList}
                className="w-[356px] rounded-lg"
                placeholder="请选择"
                notFoundContent={<NotFoundContent />}
              ></Select>
            </Form.Item>
            <Flex gap={20}>
              <Form.Item
                name="temperature"
                label={
                  <span className="font-semibold text-gray-900">
                    温度
                    <Tooltip title={EXPLANATION_TEMPERATURE}>
                      <QuestionCircleOutlined
                        style={{ color: "#666", marginLeft: "5px" }}
                      />
                    </Tooltip>
                  </span>
                }
                rules={[{ required: true }, validateNumber(0.1, 1)]}
                style={{ flex: "1" }}
              >
                <div className="w-[356px] flex justify-between items-center">
                  <Slider
                    min={0.1}
                    max={1}
                    step={0.1}
                    value={temperature}
                    onChange={(value: any) => {
                      setTemperature(value);
                      form.setFieldValue("temperature", value);
                    }}
                    className="w-[250px]"
                  />
                  <InputNumber
                    min={0.1}
                    max={1}
                    step={0.1}
                    value={temperature}
                    style={{ width: "90px", height: "32px" }}
                    onChange={(value: any) => {
                      if (isNaN(value)) return;
                      setTemperature(value);
                      form.setFieldValue("temperature", value);
                    }}
                  />
                </div>
              </Form.Item>
              <Form.Item
                name="top_p"
                label={
                  <span className="font-semibold text-gray-900">
                    多样性
                    <Tooltip title={EXPLANATION_TOP_P}>
                      <QuestionCircleOutlined
                        style={{ color: "#666", marginLeft: "5px" }}
                      />
                    </Tooltip>
                  </span>
                }
                rules={[{ required: true }, validateNumber(0.1, 1)]}
                style={{ flex: "1" }}
              >
                <div className="w-[356px] flex justify-between items-center">
                  <Slider
                    min={0.1}
                    max={1}
                    step={0.1}
                    className="w-[250px]"
                    value={diversity}
                    onChange={(value: any) => {
                      setDiversity(value);
                      form.setFieldValue("top_p", value);
                    }}
                  />
                  <InputNumber
                    min={0.1}
                    max={1}
                    step={0.1}
                    value={diversity}
                    style={{ width: "90px", height: "32px" }}
                    onChange={(value: any) => {
                      if (isNaN(value)) return;
                      setDiversity(value);
                      form.setFieldValue("top_p", value);
                    }}
                  />
                </div>
              </Form.Item>
            </Flex>
            <Flex justify="space-between" gap={20}>
              <Form.Item
                name="top_k"
                label={
                  <span className="font-semibold text-gray-900">
                    召回数
                    <Tooltip title={EXPLANATION_TOP_K}>
                      <QuestionCircleOutlined
                        style={{ color: "#666", marginLeft: "5px" }}
                      />
                    </Tooltip>
                  </span>
                }
                rules={[
                  { required: true },
                  validateNumber(configScale.top_k.min, configScale.top_k.max)
                ]}
                style={{ flex: "1" }}
              >
                <div className="w-[356px] flex justify-between items-center">
                  <Slider
                    min={configScale.top_k.min}
                    max={configScale.top_k.max}
                    step={1}
                    value={recallChunksNum}
                    className="w-[250px]"
                    onChange={(value: any) => {
                      setRecallChunkNum(value);
                      form.setFieldValue("top_k", value);
                    }}
                  />
                  <InputNumber
                    min={configScale.top_k.min}
                    max={configScale.top_k.max}
                    step={1}
                    value={recallChunksNum}
                    style={{ width: "90px", height: "32px" }}
                    onChange={(value: any) => {
                      if (isNaN(value)) return;
                      setRecallChunkNum(value);
                      form.setFieldValue("top_k", value);
                    }}
                  />
                </div>
              </Form.Item>
              <Form.Item
                name="score_threshold"
                label={
                  <span className="font-semibold text-gray-900">
                    相似度阈值
                    <Tooltip title={EXPLANATION_SIMILAR_THRESHOLD}>
                      <QuestionCircleOutlined
                        style={{ color: "#666", marginLeft: "5px" }}
                      />
                    </Tooltip>
                  </span>
                }
                rules={[{ required: true }, validateNumber(0.1, 1)]}
                style={{ flex: "1" }}
              >
                <div className="w-[356px] flex justify-between items-center">
                  <Slider
                    min={0.1}
                    max={1}
                    step={0.1}
                    className="w-[250px]"
                    value={similarThreshold}
                    onChange={(value: any) => {
                      setSimilarThreshold(value);
                      form.setFieldValue("score_threshold", value);
                    }}
                  />
                  <InputNumber
                    min={0.1}
                    max={1}
                    step={0.1}
                    value={similarThreshold}
                    style={{ width: "90px", height: "32px" }}
                    onChange={(value: any) => {
                      if (isNaN(value)) return;
                      setSimilarThreshold(value);
                      form.setFieldValue("score_threshold", value);
                    }}
                  />
                </div>
              </Form.Item>
            </Flex>
            <Flex justify="space-between" gap={20}>
              <Form.Item
                name="max_tokens"
                label={
                  <span className="font-semibold text-gray-900">
                    最大令牌数
                    <Tooltip title={EXPLANATION_MAXTOKENS}>
                      <QuestionCircleOutlined
                        style={{ color: "#666", marginLeft: "5px" }}
                      />
                    </Tooltip>
                  </span>
                }
                style={{ flex: "1" }}
                rules={[
                  { required: true },
                  validateNumber(
                    configScale.max_tokens.min,
                    configScale.max_tokens.max
                  )
                ]}
              >
                <div className="w-[356px] flex justify-between items-center">
                  <Slider
                    min={configScale.max_tokens.min}
                    max={configScale.max_tokens.max}
                    step={1}
                    value={maxToken}
                    className="w-[250px]"
                    onChange={(value: any) => {
                      setMaxToken(value);
                      form.setFieldValue("max_tokens", value);
                    }}
                  />
                  <InputNumber
                    min={configScale.max_tokens.min}
                    max={configScale.max_tokens.max}
                    step={1}
                    value={maxToken}
                    style={{ width: "90px", height: "32px" }}
                    onChange={(value: any) => {
                      if (isNaN(value)) return;
                      setMaxToken(value);
                      form.setFieldValue("max_tokens", value);
                    }}
                  />
                </div>
              </Form.Item>
              <Form.Item
                name="max_round"
                label={
                  <span className="font-semibold text-gray-900">
                    上下文最大轮数
                    <Tooltip title={EXPLANATION_MAX_ROUND}>
                      <QuestionCircleOutlined
                        style={{ color: "#666", marginLeft: "5px" }}
                      />
                    </Tooltip>
                  </span>
                }
                style={{ flex: "1" }}
                rules={[
                  { required: true },
                  validateNumber(
                    configScale.max_round.min,
                    configScale.max_round.max
                  )
                ]}
              >
                <div className="w-[356px] flex justify-between items-center">
                  <Slider
                    min={configScale.max_round.min}
                    max={configScale.max_round.max}
                    step={1}
                    value={maxRound}
                    className="w-[250px]"
                    onChange={(value: any) => {
                      setMaxRound(value);
                      form.setFieldValue("max_round", value);
                    }}
                  />
                  <InputNumber
                    min={configScale.max_round.min}
                    max={configScale.max_round.max}
                    step={1}
                    value={maxRound}
                    style={{ width: "90px", height: "32px" }}
                    onChange={(value: any) => {
                      if (isNaN(value)) return;
                      setMaxRound(value);
                      form.setFieldValue("max_round", value);
                    }}
                  />
                </div>
              </Form.Item>
            </Flex>
          </div>
          {/* 功能开关分组 */}
          <div className="mb-8">
            <div
              className="text-lg font-bold text-primary-color mb-4 border-l-4
             border-blue-200 pl-3 bg-blue-50/40 rounded"
            >
              功能开关
            </div>
            {/* 检索相关功能 */}
            <div className="space-y-3 flex flex-col gap-y-2 px-4 mb-4">
              <div className="flex items-center justify-between">
                <span
                  className={
                    set_FAQ_priority
                      ? "font-semibold text-gray-900"
                      : "text-gray-400"
                  }
                >
                  开启FAQ优先
                </span>
                <Switch
                  value={set_FAQ_priority}
                  onChange={set_set_FAQ_priority}
                />
              </div>
              <div className="flex items-center justify-between">
                <span
                  className={
                    enabled_graph
                      ? "font-semibold text-gray-900"
                      : "text-gray-400"
                  }
                >
                  启用图谱增强
                </span>
                <Switch value={enabled_graph} onChange={set_enabled_graph} />
              </div>

              <div className="flex items-center justify-between">
                <span
                  className={
                    dependOnKb ? "font-semibold text-gray-900" : "text-gray-400"
                  }
                >
                  强企业知识依赖
                  <Tooltip title={EXPLANATION_DEPENDON_KB}>
                    <QuestionCircleOutlined
                      style={{ color: "#666", marginLeft: "5px" }}
                    />
                  </Tooltip>
                </span>
                <Switch value={dependOnKb} onChange={setDependOnKb} />
              </div>
              <div className="flex items-center justify-between">
                <span
                  className={
                    enabled_question_rewrite
                      ? "font-semibold text-gray-900"
                      : "text-gray-400"
                  }
                >
                  开启问题改写
                </span>
                <Switch
                  value={enabled_question_rewrite}
                  onChange={set_enabled_question_rewrite}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className={"font-semibold text-gray-900"}>
                  检索策略：
                </span>
                <Select
                  options={[
                    { label: "混合检索", value: 1 },
                    { label: "全文检索", value: 2 },
                    { label: "语义检索", value: 3 }
                  ]}
                  style={{ width: "136px" }}
                  placeholder="请选择检索策略"
                  value={search_policy}
                  onChange={(value) => {
                    form.setFieldValue("search_policy", value);
                    set_search_policy(value);
                  }}
                ></Select>
              </div>
              <div className="flex items-center justify-between">
                <span
                  className={
                    show_similar_threshold
                      ? "font-semibold text-gray-900"
                      : "text-gray-400"
                  }
                >
                  开启精排模式
                </span>
                <Switch
                  value={show_similar_threshold}
                  onChange={set_show_similar_threshold}
                />
              </div>
              {show_similar_threshold && (
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-gray-900">
                    <span className="text-[#d70016] mr-[6px]">*</span>Rerank模型
                  </span>

                  <Form.Item
                    name="rerank_model_name"
                    validateTrigger="onChange"
                    initialValue={DEFAULT_RERANK}
                    rules={[
                      {
                        required: true,
                        validator(_: any, value: any) {
                          const options = rerankOptions || [];
                          if (!value) {
                            if (
                              Array.isArray(options) &&
                              options.length === 0
                            ) {
                              return Promise.reject(
                                "暂无可用模型，请联系管理员"
                              );
                            } else {
                              return Promise.reject("请选择Rerank模型");
                            }
                          }
                          // if (
                          //   value &&
                          //   !options.find((m: any) => m.value == value)
                          // ) {
                          //   return Promise.reject("模型无法使用，请联系管理员");
                          // }
                          return Promise.resolve();
                        }
                      }
                    ]}
                  >
                    <Select
                      style={{ width: "220px" }}
                      options={rerankOptions}
                      notFoundContent={<NotFoundContent />}
                    />
                  </Form.Item>
                </div>
              )}
            </div>
            <div className="border-t border-gray-200 my-4" />
            {/* 溯源相关功能 */}

            <div className="space-y-3 flex flex-col gap-y-2 px-4">
              <div className="flex items-center justify-between">
                <span
                  className={
                    need_trace_source
                      ? "font-semibold text-gray-900"
                      : "text-gray-400"
                  }
                >
                  是否开启溯源
                </span>
                <Switch
                  value={need_trace_source}
                  onChange={(val) => {
                    set_need_trace_source(val);
                    if (!val) {
                      set_trace_by_llm(false);
                      set_is_download(false);
                    }
                  }}
                />
              </div>

              {need_trace_source && (
                <>
                  <div className="flex items-center justify-between">
                    <span className={"font-semibold text-gray-900"}>
                      溯源策略：
                    </span>
                    <Select
                      options={[
                        { label: "规则溯源", value: false },
                        { label: "大模型溯源", value: true }
                      ]}
                      style={{ width: "136px" }}
                      placeholder="请选择溯源策略"
                      value={trace_by_llm}
                      onChange={(value) => {
                        form.setFieldValue("trace_by_llm", value);
                        set_trace_by_llm(value);
                      }}
                    ></Select>
                  </div>
                  <div className="flex items-center justify-between">
                    <span
                      className={
                        is_download
                          ? "font-semibold text-gray-900"
                          : "text-gray-400"
                      }
                    >
                      是否允许下载溯源文件
                    </span>
                    <Switch value={is_download} onChange={set_is_download} />
                  </div>
                </>
              )}
            </div>
          </div>
          {/* 敏感词与知识库分组 */}
          <div className="mb-8">
            <div
              className="text-lg font-bold text-primary-color mb-4 border-l-4
             border-blue-200 pl-3 bg-blue-50/40 rounded"
            >
              敏感词
            </div>
            <Form.Item name="sensitiveWordIds" label="">
              <SelectBox
                title="选择敏感词库"
                options={sensitiveWordsOption}
                handleChage={(value: any[]) =>
                  handleChage("sensitiveWordIds", value)
                }
                sensitiveWordIds={sensitiveWordIds}
                checkedData={checkedData}
                setCheckedData={setCheckedData}
                disabled={drawConfig?.type === "view"}
              ></SelectBox>
            </Form.Item>
            <div className="flex mb-[8px] items-center">
              <Switch
                className="mr-[8px]"
                checked={customReply}
                onChange={setCustomReply}
              />
              <span>自定义回复</span>
            </div>
            {customReply ? (
              <Form.Item
                name="defaultAnswer"
                label={
                  <span className="font-semibold text-gray-900">
                    自定义回复内容
                  </span>
                }
              >
                <TextArea
                  style={{ height: "55px", resize: "none" }}
                  className="rounded-lg"
                />
              </Form.Item>
            ) : (
              <div className="h-[20px] w-[20px]" />
            )}

            <div
              className="text-lg font-bold text-primary-color mb-4 border-l-4
             border-blue-200 pl-3 bg-blue-50/40 rounded"
            >
              知识库
            </div>
            <Form.Item name="knowledge_base_name_source" label="">
              <SelectBox
                title="选择知识库"
                options={knowledgeBaseOption}
                sensitiveWordIds={knowledge_base_name_source}
                checkedData={knowledge_base_name_source_checkedData}
                setCheckedData={setKnowledge_base_name_source_checkedData}
                disabled={drawConfig?.type === "view"}
                type="tag"
              ></SelectBox>
            </Form.Item>
            {databasePermission && (
              <>
                <div
                  className="text-lg font-bold text-primary-color mb-4 border-l-4
             border-blue-200 pl-3 bg-blue-50/40 rounded"
                >
                  数据库
                </div>
                <Form.Item name="database_name_source" label="">
                  <SelectBox
                    title="选择数据库"
                    options={databaseOptions}
                    sensitiveWordIds={database_name}
                    checkedData={database_source_checkData}
                    setCheckedData={setDatabase_source_checkData}
                    disabled={drawConfig?.type === "view"}
                    max={10}
                  ></SelectBox>
                </Form.Item>
              </>
            )}
          </div>
        </Form>
      </Flex>
      <Flex
        justify="space-between"
        align="center"
        className="h-[70px] px-[20px]"
        style={{ borderTop: "1px solid #D9D9D9" }}
      >
        <div className="flex">
          <Switch
            className="mr-[8px]"
            value={isDefault}
            onChange={(checked) => setIsDefault(checked)}
            disabled={drawConfig?.type === "view"}
          />
          <div className="mr-[20px]">选择为默认助手</div>
        </div>
        <Flex justify="center" align="center">
          <Button
            className="ml-[10px]"
            onClick={() => props.onCancel && props.onCancel()}
            disabled={drawConfig?.type === "view"}
          >
            取消
          </Button>
          <Button
            className="ml-[10px]"
            type="primary"
            onClick={handleUpdate}
            loading={btnLoading}
            disabled={drawConfig?.type === "view"}
          >
            确定
          </Button>
          {/* {drawConfig.type == "create" ? (
            <></>
          ) : (
            <Button
              className="ml-[10px]"
              onClick={confirmDelete}
              style={{
                border: "1px solid red",
                color: "red",
                backgroundColor: "#fff"
              }}
            >
              删除
            </Button>
          )} */}
        </Flex>
      </Flex>

      <Modal
        className="nlp-setting-edit-modal"
        title="是否删除"
        okText="确认"
        cancelText="取消"
        open={isModalShow}
        onOk={handleDelete}
        onCancel={() => setIsModalShow(false)}
      >
        是否要删除该配置?
      </Modal>
    </Flex>
  );
};

const ISettingDetail = (props: any) => {
  const {
    drawConfig,
    setOpenDraw,
    openDraw,
    fetchConfigList,
    configData,
    curMenuKey,
    fetchConfigShareList
  } = props;

  const [btnLoading, setBtnLoading] = useState(false);
  const [knowledgeBaseOption, setKnowledgeBaseOption] = useState([]);
  const [knowledgeShareBaseOption, setKnowledgeShareBaseOption] = useState([]);
  const { id } = useParams();
  const navigator = useNavigate();

  const FLAT_BREAD_CRUMB = [
    {
      href: "/chats/setting",
      title: (
        <>
          <HomeOutlined />
          <span>检索配置</span>
        </>
      )
    }
  ];

  if (drawConfig.type == "create") {
    FLAT_BREAD_CRUMB.push({
      href: `/chats/setting/create`,
      title: (
        <>
          <span>新增</span>
        </>
      )
    });
  } else if (drawConfig.type == "edit") {
    FLAT_BREAD_CRUMB.push({
      href: `/chats/setting/edit/${id}`,
      title: (
        <>
          <span>编辑</span>
        </>
      )
    });
  }

  useEffect(() => {
    if (
      curMenuKey === "2" &&
      (drawConfig.type === "edit" || drawConfig.type === "view")
    ) {
      fetchKnowledgeBase(
        `${getUrlPrefix()}/index/knowledgeBase/searchList?userName=${
          drawConfig.data.createBy
        }`
      );
    }
  }, [drawConfig]);

  const handleDeleteConfig = (key: any) => {
    if (key) {
      setBtnLoading(true);
      axios$
        .delete(`${getUrlPrefix()}/qa/search/config/deleteById?configId=${key}`)
        .then((res: any) => {
          curMenuKey === "1" ? fetchConfigList() : fetchConfigShareList();
          message.success("配置删除成功", 2);
        })
        .finally(() => setBtnLoading(false));
    }
  };

  const handleColumnUpdate = (data: any) => {
    const isDefault = data.isDefault ? 1 : 0;
    // const set_FAQ_priority = data.set_FAQ_priority ? 1 : 0; //放入reqJSON 20241023by吴登峰

    data.enabled_faq = data.set_FAQ_priority;
    data.enabled_rerank = data.show_similar_threshold; //使用布尔类型 20241023 ? 1 : 0;
    // data.knowledge_base_name_source = (data.knowledge_base_name_source || []).join(";");
    // 20241108修改 begin
    // 将原字段knowledge_base_name改为knowledge_base_name_source，存储kbName
    // knowledge_base_name存储primitiveName
    data.dependOnKb = data.dependOnKb ? 1 : 0;

    // 20241108修改 end
    const req_params_pre = JSON.parse(JSON.stringify(data));
    delete req_params_pre.key;
    delete req_params_pre.show_similar_threshold;
    delete req_params_pre.enabledFaq;
    delete req_params_pre.isDefault;
    delete req_params_pre.set_FAQ_priority;
    delete req_params_pre.sensitiveWordIds;
    delete req_params_pre.configJson;
    delete req_params_pre.createBy;
    delete req_params_pre.des;
    delete req_params_pre.description;
    delete req_params_pre.model;
    delete req_params_pre.permission;
    delete req_params_pre.gmtCreate;
    delete req_params_pre.id;
    delete req_params_pre.name;

    const req_params = JSON.stringify(req_params_pre);

    setBtnLoading(true);
    axios$
      .put(`${getUrlPrefix()}/qa/search/config/update`, {
        isDefault,
        // enabledFaq: set_FAQ_priority, //放入reqJSON 20241023by吴登峰
        id: data.key,
        configJson: req_params,
        name: data.config_name,
        des: data.description,
        sensitiveWordIds: data.sensitiveWordIds
          ? data.sensitiveWordIds.join(",")
          : [],
        defaultAnswer: data.defaultAnswer,
        dependOnKb: data.dependOnKb,
        need_trace_source: data.need_trace_source,
        trace_by_llm: data.trace_by_llm,
        is_download: data.is_download,
        enabled_question_rewrite: data.enabled_question_rewrite,
        search_policy: data.search_policy
      })
      .then((res: any) => {
        if (res.success) {
          message.success("配置编辑成功!");
          curMenuKey === "1" ? fetchConfigList() : fetchConfigShareList();
          // 不需要调用这个接口 20250909by吴登峰
          // if (data.isDefault) {
          //   handleSetDefault(data);
          // } else {
          //   setOpenDraw(false);
          // }
          setOpenDraw(false);
        } else {
          message.success("配置编辑失败!");
        }
      })
      .finally(() => setBtnLoading(false));
  };

  const handleConfigCreate = (formCreate: any) => {
    if (!formCreate?.top_k) {
      formCreate["top_k"] = 10;
    }

    const isDefault = formCreate.isDefault ? 1 : 0;
    // const set_FAQ_priority = formCreate.set_FAQ_priority  ? 1 : 0;  放入reqJSON 20241023by吴登峰，show_similar_threshold同
    formCreate.enabled_faq = formCreate.set_FAQ_priority; //使用布尔类型，20241023by吴登峰
    // const show_similar_threshold = formCreate.show_similar_threshold ? 1 : 0;
    formCreate.enabled_rerank = formCreate.show_similar_threshold;
    formCreate.dependOnKb = formCreate.dependOnKb ? 1 : 0;
    delete formCreate.isDefault;
    delete formCreate.set_FAQ_priority;
    delete formCreate.show_similar_threshold;
    const reqJSON = JSON.stringify(formCreate);

    setBtnLoading(true);
    axios$
      .post(`${getUrlPrefix()}/qa/search/config/add`, {
        isDefault,
        // enabledFaq: set_FAQ_priority,  //放入reqJSON 20241023by吴登峰
        configJson: reqJSON,
        sensitiveWordIds: formCreate["sensitiveWordIds"].join(","),
        defaultAnswer: formCreate["defaultAnswer"],
        name: formCreate["config_name"],
        des: formCreate["description"],
        dependOnKb: formCreate.dependOnKb,
        need_trace_source: formCreate.need_trace_source,
        trace_by_llm: formCreate.trace_by_llm,
        is_download: formCreate.is_download,
        enabled_question_rewrite: formCreate.enabled_question_rewrite,
        search_policy: formCreate.search_policy
      })
      .then(() => {
        message.success("配置新建成功!");
        curMenuKey === "1" ? fetchConfigList() : fetchConfigShareList();
        setOpenDraw(false);
      })
      .finally(() => setBtnLoading(false));
  };

  const fetchKnowledgeBase = async (url?: string) => {
    try {
      axios$
        // 20241125 应吴登峰要求修改接口，此接口无分页
        .get(url || `${getUrlPrefix()}/index/knowledgeBase/searchList`)
        .then((result: any) => {
          if (result?.data) {
            const format_data = result?.data.map((kb: any) => {
              return {
                id: kb.kbName,
                name: kb.kbName,
                knowledge_base_name_source: kb.primitiveName,
                knowledge_base_name: kb.kbName,
                kbId: kb.id
              };
            });
            url
              ? setKnowledgeShareBaseOption(format_data)
              : setKnowledgeBaseOption(format_data);
          }
        });
    } catch (error) {
      console.log("e", error);
    }
  };

  const options = useMemo(() => {
    return curMenuKey === "1" ? knowledgeBaseOption : knowledgeShareBaseOption;
  }, [curMenuKey, knowledgeBaseOption, knowledgeShareBaseOption]);

  useEffect(() => {
    if (curMenuKey === "2") return;
    fetchKnowledgeBase();
  }, []);

  return (
    <SettingDetail
      knowledgeBaseOption={options}
      configNameList={configData}
      onUpdate={handleColumnUpdate}
      onCancel={() => setOpenDraw(false)}
      onDelete={handleDeleteConfig}
      onCreate={handleConfigCreate}
      btnLoading={btnLoading}
      openDraw={openDraw}
      knowledgeShareBaseOption={knowledgeShareBaseOption}
      {...props}
    />
  );
};

export default ISettingDetail;
