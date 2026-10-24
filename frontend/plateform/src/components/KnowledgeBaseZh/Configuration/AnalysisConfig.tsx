import "@/assets/styles/knowledgebaseNew.less";
import { QuestionCircleOutlined } from "@ant-design/icons";
import {
  Button,
  Form,
  InputNumber,
  message,
  Select,
  Tooltip,
  Slider,
  Flex,
  Switch,
  Radio,
  Input
} from "antd";
import { useEffect, useState } from "react";
import { updateConf } from "./service";
import {
  getConfigEditStatus,
  getEmbeddingModels,
  getParseTypes
} from "../KnowledgeAnalyBlock/service";
import { IConfiguration } from ".";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
import { useLocation, useParams } from "react-router-dom";

const { useForm } = Form;

const AnalysisConfig = (props: IConfiguration) => {
  const { kbInfo, settingOpt } = props;
  const [form] = useForm();
  const [chunkSize, setChunk_size]: any = useState(500);
  const [similarQuestionMaxNums, setSimilarQuestionMaxNums]: any = useState(1);
  const [fileFaqMaxNums, setFileFaqMaxNums]: any = useState();
  const [btnLoading, setBtnLoading] = useState(false);

  const sliderChange = (value: number | null, key: string) => {
    switch (key) {
      case "chunkSize":
        setChunk_size(value);
        form.setFieldValue(key, value);
        break;
      case "fileFaqMaxNums":
        setFileFaqMaxNums(value === 1001 ? Infinity : value);
        form.setFieldValue(key, value === 1001 ? Infinity : value);
        break;
      case "similarQuestionMaxNums":
        setSimilarQuestionMaxNums(value);
        form.setFieldValue(key, value);
        break;
    }
  };

  const updateConfFn = async (data: any) => {
    try {
      setBtnLoading(true);
      const res = await updateConf(data);
      setBtnLoading(false);
      if (res) {
        message.success("保存解析配置成功");
      }
    } catch (e) {
      console.log(e);
      setBtnLoading(false);
    }
  };

  const toSubmit = () => {
    form.validateFields().then((data: any) => {
      console.log("params", data);
      updateConfFn({
        ...data,
        id: kbInfo.id,
        fileFaqMaxNums:
          data.fileFaqMaxNums === Infinity ? 0 : data.fileFaqMaxNums
      });
    });
  };

  useEffect(() => {
    if (kbInfo) {
      const { fileType, id } = kbInfo;
      if (fileType) {
        form.setFieldValue("fileType", kbInfo.fileType);
        form.setFieldValue("embeddingModelName", kbInfo.embeddingModelName);
        form.setFieldValue("graphPrompt", kbInfo.graphPrompt);
        form.setFieldValue("chunkSize", kbInfo.chunkSize);
        setChunk_size(kbInfo.chunkSize);
        const f = !kbInfo.fileFaqMaxNums ? Infinity : kbInfo.fileFaqMaxNums;
        form.setFieldValue("fileFaqMaxNums", f);
        setFileFaqMaxNums(f);
        const s = !kbInfo.similarQuestionMaxNums
          ? 1
          : kbInfo.similarQuestionMaxNums;
        form.setFieldValue("similarQuestionMaxNums", s);
        setSimilarQuestionMaxNums(s);
      } else {
        setFileFaqMaxNums(Infinity);
      }
    } else {
      setFileFaqMaxNums(Infinity);
    }
  }, [kbInfo]);

  const [embeddingModelsOption, setEmbeddingModelsOption] = useState([]);
  const [parseMethodOption, setParseMethodOption] = useState([]);

  const getEmbedding = async () => {
    try {
      const res: any = await getEmbeddingModels();
      if (form.getFieldValue("embeddingModelName")) {
        form.setFieldValue(
          "embeddingModelName",
          res.find((item: any) => item.isDefault)?.name
        );
      }
      setEmbeddingModelsOption(
        res.map((item: any) => {
          return { value: item.name, label: item.name };
        })
      );
    } catch (error) {
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };
  const getParseMethods = async () => {
    try {
      const res: any = await getParseTypes();
      if (form.getFieldValue("embeddingModelName")) {
        form.setFieldValue(
          "embeddingModelName",
          res.find((item: any) => item.isDefault)?.name
        );
      }
      setParseMethodOption(
        res.map((item: any) => {
          return { value: item.name, label: item.name };
        })
      );
    } catch (error) {
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const disabled = getBtnDisabled(FILE_BTN.ANALYSIS_CONFIG, kbInfo.permission);

  useEffect(() => {
    getParseMethods();
    getEmbedding();
  }, []);

  return (
    <div className="relative w-full flex justify-center">
      <div className="form-wrap w-[552px] h-[calc(100%-50px)] overflow-y-auto overflow-x-hidden px-[16px]">
        <Form
          form={form}
          labelCol={{ span: 8 }}
          wrapperCol={{ span: 20 }}
          initialValues={{
            fileType: "intelligent",
            chunkSize: 500,
            fileFaqMaxNums: Infinity,
            similarQuestionMaxNums: 1,
            enablePolish: false
          }}
        >
          {(!settingOpt || settingOpt.embeddingModelName) && (
            <>
              <div className="label-wrap">
                <b>*</b>
                <span>嵌入模型</span>
                <Tooltip title="用于嵌入块的嵌入模型，一旦更改，整个知识库要重新构建索引。">
                  <QuestionCircleOutlined />
                </Tooltip>
              </div>
              <Form.Item
                label={false}
                name="embeddingModelName"
                rules={[{ required: true, message: "请选择嵌入模型" }]}
              >
                <Select
                  style={{ width: "520px" }}
                  disabled={getBtnDisabled(
                    FILE_BTN.ANALYSIS_CONFIG,
                    kbInfo.permission
                  )}
                  options={embeddingModelsOption}
                />
              </Form.Item>
            </>
          )}

          {/* {(!settingOpt || settingOpt.chunkStrategy) && (
            <Form.Item
              label={false}
              name="chunkStrategy"
              rules={[{ required: true }]}
            >
              <Radio.Group defaultValue="naive">
                <Radio value="naive">智能切分</Radio>
                <Radio value="intelligent">自定义切片</Radio>
              </Radio.Group>
            </Form.Item>
          )} */}

          {(!settingOpt || settingOpt.fileType) && (
            <>
              <div className="label-wrap">
                <b>*</b>
                <span>解析方法</span>
                <Tooltip title="支持的解析方法为智能通用、规章制度、书籍。">
                  <QuestionCircleOutlined />
                </Tooltip>
              </div>
              <Form.Item
                label={false}
                name="fileType"
                rules={[{ required: true, message: "请选择解析方法" }]}
              >
                <Select
                  style={{ width: "520px" }}
                  disabled={disabled}
                  options={[
                    {
                      label: "financial",
                      value: "financial"
                    }
                  ]}
                />
              </Form.Item>
            </>
          )}

          {(!settingOpt || settingOpt.graphPrompt) && (
            <>
              <div className="label-wrap">
                <span>抽取实体类型</span>
              </div>
              <Form.Item label={false} name="graphPrompt">
                <Input
                  style={{ width: "520px" }}
                  disabled={disabled}
                  placeholder="请输入需要抽取的实体类型，多个类型可以用逗号隔开"
                />
              </Form.Item>
            </>
          )}

          {(!settingOpt || settingOpt.chunkSize) && (
            <>
              <div className="label-wrap">
                <span>块Token数</span>
                <Tooltip title="用于切分文本块的大小限制，更改后整个知识库需要重新构建索引。">
                  <QuestionCircleOutlined />
                </Tooltip>
              </div>
              <div className="flex">
                <div className="l">
                  <Form.Item label={false} name="chunkSize">
                    <Slider
                      disabled={disabled}
                      style={{ width: "420px" }}
                      min={100}
                      max={1000}
                      styles={{
                        rail: { backgroundColor: "#d9d9d9", height: 4 },
                        track: { backgroundColor: "#2468f2", height: 4 }
                      }}
                      onChange={(value) => {
                        sliderChange(value, "chunkSize");
                      }}
                      value={typeof chunkSize === "number" ? chunkSize : 0}
                    />
                  </Form.Item>
                </div>
                <div className="r">
                  <InputNumber
                    disabled={disabled}
                    min={100}
                    max={1000}
                    value={chunkSize}
                    onChange={(value) => {
                      sliderChange(value, "chunkSize");
                    }}
                  />
                </div>
              </div>
            </>
          )}

          <Flex justify="space-between">
            <div>
              {(!settingOpt || settingOpt.fileFaqMaxNums) && (
                <>
                  <div className="label-wrap">
                    <span>单篇文档问答对抽取数量上限</span>
                    {/* <Tooltip title="用于切分文本块的大小限制，更改后整个知识库需要重新构建索引。">
                  <QuestionCircleOutlined />
                </Tooltip> */}
                  </div>
                  <div className="flex">
                    <div className="l mr-[8px]">
                      <Form.Item label={false} name="fileFaqMaxNums">
                        <Slider
                          disabled={disabled}
                          style={{ width: "140px" }}
                          min={1}
                          max={1001}
                          styles={{
                            rail: { backgroundColor: "#d9d9d9", height: 4 },
                            track: { backgroundColor: "#2468f2", height: 4 }
                          }}
                          onChange={(value) => {
                            sliderChange(value, "fileFaqMaxNums");
                          }}
                          value={
                            typeof fileFaqMaxNums === "number"
                              ? fileFaqMaxNums
                              : 0
                          }
                          tooltip={{
                            formatter: (value) => {
                              return value == 1001 ? "无限大" : value;
                            }
                          }}
                        />
                      </Form.Item>
                    </div>
                    <div className="r">
                      <InputNumber
                        disabled={disabled}
                        min={1}
                        max={1001}
                        value={fileFaqMaxNums}
                        formatter={(value) => {
                          return value == 1001 ||
                            value === Infinity ||
                            value === "Infinity"
                            ? "无限大"
                            : value;
                        }}
                        onChange={(value) => {
                          sliderChange(value, "fileFaqMaxNums");
                        }}
                      />
                    </div>
                  </div>
                </>
              )}
            </div>

            <div>
              {(!settingOpt || settingOpt.similarQuestionMaxNums) && (
                <>
                  <div className="label-wrap">
                    <span>生成相似问个数</span>
                    <Tooltip title="使用大模型自动生成相似问">
                      <QuestionCircleOutlined />
                    </Tooltip>
                  </div>
                  <div className="flex">
                    <div className="l mr-[8px]">
                      <Form.Item label={false} name="similarQuestionMaxNums">
                        <Slider
                          disabled={disabled}
                          style={{ width: "140px" }}
                          min={1}
                          max={3}
                          styles={{
                            rail: { backgroundColor: "#d9d9d9", height: 4 },
                            track: { backgroundColor: "#2468f2", height: 4 }
                          }}
                          onChange={(value) => {
                            sliderChange(value, "similarQuestionMaxNums");
                          }}
                          value={
                            typeof similarQuestionMaxNums === "number"
                              ? similarQuestionMaxNums
                              : 0
                          }
                        />
                      </Form.Item>
                    </div>
                    <div className="r">
                      <InputNumber
                        disabled={disabled}
                        min={1}
                        max={3}
                        value={similarQuestionMaxNums}
                        onChange={(value) => {
                          sliderChange(value, "similarQuestionMaxNums");
                        }}
                      />
                    </div>
                  </div>
                </>
              )}
            </div>
          </Flex>
          {/* <div className="label-wrap">
            <span>FAQ导入是否需要润色</span>
          </div>
          <Form.Item label={false} name="enablePolish">
            <Switch />
          </Form.Item> */}
        </Form>
        <div className="analysis-config-btn-group">
          {/* <Button
            style={{
              border: "1px solid #ebebeb",
              color: "#555"
            }}
            onClick={() => {}}
          >
            取消
          </Button> */}
          <Button
            style={{
              background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
              color: disabled ? "#ddd" : "#fff"
            }}
            className="border-none"
            disabled={disabled}
            loading={btnLoading}
            onClick={toSubmit}
          >
            保存
          </Button>
        </div>
      </div>
    </div>
  );
};

export default AnalysisConfig;
