import {
  DeleteOutlined,
  DownCircleOutlined,
  PlusCircleOutlined
} from "@ant-design/icons";
import {
  Button,
  Card,
  Flex,
  Form,
  FormInstance,
  Input,
  Popconfirm,
  theme,
  Typography
} from "antd";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useDrag, useDrop } from "react-dnd";
import { ItemInfo } from "../type";
import { getItemInfo, isChildren } from "../util";
import { OutlineData } from "../@types";

const { TextArea } = Input;

interface Iprops {
  itemData: Omit<OutlineData, "children">;
  outlineData: OutlineData[];
  limit?: number;
  form: FormInstance<any>;
  outlinesEventEmit?: (title: string, data: any) => void;
}

// 标题左边点的色轮
const colorWheel = ["#8e81f0", "#38c6d9", "#f2b149"];

const OutlineItem = (props: Iprops) => {
  const { itemData, outlineData, limit = 3, form, outlinesEventEmit } = props;
  const { useToken } = theme;
  const { token } = useToken();
  const { colorPrimary } = token;
  const [introCollapsed, setIntroCollapsed] = useState<boolean>(false);
  const ref = useRef<any>(null);

  // 当前项的信息，位置和深度
  const [itemInfo, setItemInfo] = useState<ItemInfo | null>(null);

  useEffect(() => {
    if (!form || !itemData) return;
    form.setFieldsValue({
      [itemData.id + "[@]title"]: itemData.title,
      [itemData.id + "[@]contentAbstract"]: itemData.contentAbstract
      // [itemData.id + 'doc']: itemData.doc,
    });
  }, [form, itemData]);

  useEffect(() => {
    if (!outlineData || !itemData) return;
    setItemInfo(getItemInfo(itemData.id, outlineData));
  }, [outlineData, itemData]);

  const verticalLineStyles = useCallback(
    (index: number, itemInfo: ItemInfo | null) => {
      if (itemInfo == null) return {};
      const { depth, location, onlyOne } = itemInfo;
      if (depth + 1 > limit) {
        throw new Error(`Outlines组件initData数据最多不能超过${limit}层`);
      }
      //这一块计算的是item左边父级的竖线，最后一个item的子级不需要补充外面的竖线，其他都需要补全
      if (index !== 0 && depth !== 0) {
        if (!itemData || !outlineData || !outlineData.length) return {};
        const len = outlineData.length;
        if (isChildren(outlineData[len - 1], itemData.id)) {
          return {};
        }
        return {
          top: 0,
          height: "100%"
        };
      }

      // 理论上不会出现onlyOne为true, location为bottom的情况，优先把location赋值为top
      // 这一块计算的是当前item自己的竖线
      if (onlyOne) {
        switch (location) {
          case "top":
            return {
              top: 0,
              height: depth === 0 ? 0 : "50%"
            };
          case "center":
            return {
              top: 0,
              height: "100%"
            };
          case "bottom":
            return {
              top: "50%",
              height: depth === 0 ? 0 : "50%"
            };
          default:
            return {};
        }
      } else {
        switch (location) {
          case "top":
            return {
              top: depth === 0 ? "50%" : 0,
              height: depth === 0 ? "50%" : "100%"
            };
          case "center":
            return {
              top: 0,
              height: "100%"
            };
          case "bottom":
            return {
              top: 0,
              height: "50%"
            };
          default:
            return {};
        }
      }
    },
    [itemData, outlineData]
  );

  const handleCollapsed = () => {
    setIntroCollapsed(!introCollapsed);
  };

  const collapsedStyles = useMemo(() => {
    return introCollapsed
      ? {
          height: 0,
          display: "none"
        }
      : {};
  }, [introCollapsed]);

  const unfoldStyles = useMemo(() => {
    return introCollapsed ? {} : { height: 0, display: "none" };
  }, [introCollapsed]);

  const handleDelItem = () => {
    outlinesEventEmit && outlinesEventEmit("outlines_delItem", itemData);
  };

  const handleAddItem = () => {
    outlinesEventEmit && outlinesEventEmit("outlines_addItem", itemData);
  };

  const handleMoveToTop = (dragItem, dropItem) => {
    outlinesEventEmit &&
      outlinesEventEmit("outlines_moveToTop", {
        outlineData,
        dragItem,
        dropItem
      });
  };

  const handleMoveToBottom = (dragItem, dropItem) => {
    outlinesEventEmit &&
      outlinesEventEmit("outlines_moveToBottom", {
        outlineData,
        dragItem,
        dropItem
      });
  };

  // 拖拽源
  const [{ isDragging }, drag] = useDrag(() => ({
    type: "box",
    item: { itemData },
    collect: (monitor) => ({
      isDragging: monitor.isDragging()
    })
  }));

  const [_, drop] = useDrop(
    () => ({
      accept: "box",
      drop: (item: { itemData: Omit<OutlineData, "children"> }, monitor) => {
        // 处理拖拽事件
        const dragItem = item.itemData;
        const dropItem = itemData;
        // 拖动到原来的位置，不做任何处理
        if (dragItem.id === dropItem.id) return;

        // 使用坐标判断dragItem应该放在dropItem的上面还是下面
        const clientOffset: any = monitor.getClientOffset();
        const hoverBoundingRect = ref.current.getBoundingClientRect();
        const dragItemY = clientOffset.y;
        const dropItemY = hoverBoundingRect.y;
        const dropItemHeight = hoverBoundingRect.height;
        if (dragItemY > dropItemHeight / 2 + dropItemY) {
          // 放置在dropItem下面
          handleMoveToBottom(dragItem, dropItem);
        } else {
          // 放置在dropItem上面
          handleMoveToTop(dragItem, dropItem);
        }
      },
      collect: (monitor) => ({
        isOver: monitor.isOver()
      })
    }),
    [outlineData]
  );

  useEffect(() => {
    drag(drop(ref));
  }, []);

  const handleChange = ({
    key,
    value
  }: {
    key: "title" | "contentAbstract";
    value: string;
  }) => {
    outlinesEventEmit &&
      outlinesEventEmit("outlines_changeItem", {
        itemData,
        key,
        value
      });
  };

  return (
    <Flex
      justify="space-between"
      className={"outline-item"}
      ref={ref}
      style={{
        opacity: isDragging ? 0.5 : 1,
        cursor: "move"
      }}
    >
      {/* {itemInfo &&
        Array.from({ length: itemInfo.depth + 1 }).map((_, index) => {
          return (
            <div
              key={uid(32)}
              style={{
                position: 'absolute',
                width: '10px',
                left: `${index * -30 - 15}px`,
                borderLeft: '1px solid #ccc',
                ...verticalLineStyles(index, itemInfo),
              }}
            ></div>
          );
        })} */}
      <div className="flex-1 py-1">
        <Card
          size="small"
          className="flex-1 w-full"
          style={
            // isDragging
            //   ? {
            //       border: `1px solid ${colorPrimary || '#1166EF'}`,
            //     }
            //   : {}
            {
              background: "#F4F5F7"
            }
          }
        >
          <Flex>
            <div></div>
            <Flex vertical className="w-full">
              <Flex align="center" className="mb-[8px]">
                <Flex flex={1} align="center">
                  {/* <span
                  style={{
                    display: 'block',
                    marginRight: '5px',
                    height: '8px',
                    width: '8px',
                    borderRadius: '999px',
                    backgroundColor:
                      itemInfo?.depth && itemInfo?.depth !== -1
                        ? colorWheel[itemInfo.depth % 3]
                        : '#8e81f0',
                  }}
                /> */}

                  {/* <Text style={{ ...unfoldStyles, width: '250px' }} ellipsis={true}>
                    {itemData.title}
                  </Text> */}

                  <Flex className="w-full" style={collapsedStyles}>
                    <Form.Item
                      className="w-full"
                      name={itemData.id + "[@]title"}
                      rules={[
                        {
                          required: true,
                          message: "请填写大纲标题"
                        },
                        {
                          max: 50,
                          message: "最多五十字"
                        }
                      ]}
                    >
                      <Input
                        placeholder="请输入标题"
                        onChange={(e) =>
                          handleChange({ key: "title", value: e.target.value })
                        }
                      />
                    </Form.Item>
                  </Flex>
                </Flex>
              </Flex>
              <Flex vertical gap={10} style={collapsedStyles}>
                <Form.Item
                  name={itemData.id + "[@]contentAbstract"}
                  required
                  rules={[
                    {
                      max: 500,
                      message: "最多五百字"
                    }
                  ]}
                >
                  <TextArea
                    onChange={(e) =>
                      handleChange({
                        key: "contentAbstract",
                        value: e.target.value
                      })
                    }
                    placeholder="例如：找出政策、科技、金融等相关的情报，并提取100字内摘要。提取情报主体，按照[主体:摘要]的格式，将情报排序"
                    autoSize={{
                      minRows: 4,
                      maxRows: 4
                    }}
                    style={{ height: "100px" }}
                  />
                </Form.Item>
                {/* <Form.Item name={itemData.id + 'doc'}>
                <Select
                  placeholder="请选择知识库"
                  options={(itemData?.sources || []).map((item) => {
                    return {
                      label: item,
                      value: item,
                    };
                  })}
                  mode="multiple"
                />
              </Form.Item> */}
              </Flex>
            </Flex>

            <Flex>
              {itemInfo && itemInfo?.depth + 1 !== limit && (
                <Button
                  type="link"
                  size="small"
                  icon={<PlusCircleOutlined onClick={handleAddItem} />}
                />
              )}
              <Popconfirm
                title="确认删除"
                description="确认删除段落？删除后，内容无法恢复"
                okText="确定"
                cancelText="取消"
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
                onConfirm={handleDelItem}
              >
                <Button
                  type="link"
                  size="small"
                  icon={<DeleteOutlined style={{ color: "#999999" }} />}
                />
              </Popconfirm>
              {/* <Button
                  type="link"
                  size="small"
                  icon={<DownCircleOutlined rotate={introCollapsed ? 0 : 180} />}
                  onClick={handleCollapsed}
                /> */}
            </Flex>
          </Flex>
        </Card>
      </div>
    </Flex>
  );
};

export default OutlineItem;
