import React, { useState, useEffect } from "react";
import { Button, Spin, message, Empty, Drawer, Tooltip, Checkbox } from "antd";
import type { GetProp } from "antd";
import { PlusCircleOutlined } from "@ant-design/icons";
import {
  getIndicatorCheck,
  saveIndicatorCheck,
  deleteIndicatorCheck
} from "../common/useIndicatorsService";
import {
  useSplitLayout,
  EventTypes
} from "@/components/SplitLayout/SplitLayoutContext";
import Item from "./ArticulationItem";
import IndicatorEditor from "@/components/IndicatorEditor";
import { PrimaryBtn } from "@/pages/HomePage/Writing/common/components/PrimaryBtn";
import { CloseOutlined } from "@ant-design/icons";
import { FilterIcon } from "@/components/Icon";
import { sourceList } from "../ListItem";

export enum editTypeObj {
  checkName = "checkName",
  calculators = "calculators",
  description = "description"
}

export enum changeType {
  CALCULATOR_CLICK = "calculator",
  DELETE = "delete",
  ADD_NODE = "addNode",
  EDIT_ROW = "editRow",
  EDIT_INIT = "editInit"
}

enum status {
  ENABLE = 1,
  DISABLE = 2
}

const initialDrawerData = {
  open: false,
  curCalculator: null
};

export const initialRow = {
  id: "wcidfu",
  checkName: "",
  calculators: [],
  state: status.DISABLE
};

const Articulation: React.FC = () => {
  const [isLoading, setIsloading] = useState<boolean>(false);
  const [sourceTypeList, setSourceTypeList] = useState<any[]>([]);
  const [list, setList] = useState<any[]>([]);
  const [filterList, setFilterList] = useState<any[]>([]);
  const [editId, setEditId] = useState<string>("");
  const [editType, setEditType] = useState<string>("");
  const [isShowFilter, setIsShowFilter] = useState<boolean>(false);
  const [calculatorInfo, setCalculatorInfo] = useState<any>({
    ...initialDrawerData
  });

  const { useSubscribe, publish } = useSplitLayout();

  useSubscribe<number>(EventTypes.SAVE_CALCULATOR, (calculators: any) => {
    if (calculatorInfo.curCalculator && calculatorInfo.curCalculator.id) {
      const { checkName, id } = calculatorInfo.curCalculator;
      const params = {
        checkName,
        calculators,
        id,
        state:
          checkName && calculators && calculators.length
            ? status.ENABLE
            : status.DISABLE
      };
      editCalculators(params);
    }
  });

  const publishCaclutorsSave = () => {
    publish(EventTypes.SAVE_CALCULATOR_CONFIRM, {});
  };

  const publishCalculatorSaveId = (id: string) => {
    publish(EventTypes.SAVE_CALCULATOR_ID, id);
  };

  const fetchList = (p?: any) => {
    const params = {
      ...p
    };

    setIsloading(true);
    getIndicatorCheck(params)
      .then((res: any) => {
        setList([...res]);
        setFilterList([...res]);
      })
      .finally(() => {
        setIsloading(false);
      })
      .catch((e) => {
        console.log(e);
        setIsloading(false);
      });
  };

  const addRow = () => {
    if (!list.some((i: any) => i.id === initialRow.id)) {
      const _list = [{ ...initialRow }, ...list];
      setList([..._list]);
      setFilterList([..._list]);
      setEditId(initialRow.id);
      setEditType(editTypeObj.checkName);
    }
  };

  const rowDataChange = (row: any, type: changeType, obj?: any) => {
    const { id, calculators } = row;
    const { checkName, editIptType } = obj;
    let isEditChange = false;

    switch (type) {
      case changeType.ADD_NODE:
        if (checkName === row.checkName) {
          if (!checkName) {
            deleteNode();
          }
          resetEdit();
        } else {
          const params = {
            checkName,
            state: status.DISABLE
          };
          addNode(params);
        }
        break;
      case changeType.EDIT_ROW:
        if (checkName !== undefined && checkName !== row.checkName) {
          isEditChange = true;
          const params =
            calculators && calculators.length
              ? {
                  checkName,
                  id,
                  state: status.ENABLE,
                  calculators
                }
              : {
                  checkName,
                  id,
                  state: status.DISABLE
                };
          editNode({ ...params });
        }
        if (!isEditChange) {
          resetEdit();
        }
        break;
      case changeType.CALCULATOR_CLICK:
        setCalculatorInfo({
          ...calculatorInfo,
          open: true,
          curCalculator: row
        });
        break;
      case changeType.DELETE:
        deleteNode(id);
        break;
      case changeType.EDIT_INIT:
        setEditId(id);
        setEditType(editIptType);
        break;
    }
  };

  const addNode = (params: any) => {
    editIndicatorCheck(params, (res?: any) => {
      if (res) {
        reNewList(res, initialRow.id);
        message.success("新建校验项成功！");
        resetEdit();
      }
    });
  };

  const editNode = (params: any) => {
    editIndicatorCheck(params, (res?: any) => {
      if (res) {
        reNewList(res, params.id);
        resetEdit();
      }
    });
  };

  const editCalculators = (params: any) => {
    setIsloading(true);
    editIndicatorCheck(params, (res?: any) => {
      if (res) {
        reNewList(res, params.id);
        closeCalculatorDrawer();
        publishCalculatorSaveId(params.id);
        message.success("公式保存成功！");
      }
    });
  };

  const editIndicatorCheck = (params: any, cb?: any) => {
    setIsloading(true);
    saveIndicatorCheck(params)
      .then((res: any) => {
        if (res) {
          cb && cb(res);
        }
      })
      .finally(() => {
        setIsloading(false);
      })
      .catch((e) => {
        setIsloading(false);
      });
  };

  const reNewList = (row: any, id: string) => {
    const _list = [...list];
    const idx = _list.findIndex((i: any) => i.id === id);
    if (idx >= 0) {
      if (row && row.id) {
        _list.splice(idx, 1, { ...row });
      } else {
        _list.splice(idx, 1);
      }
      setList([..._list]);
      confirmFilter([..._list]);
    }
  };

  const resetEdit = () => {
    setEditId("");
    setEditType("");
  };

  const closeCalculatorDrawer = () => {
    setCalculatorInfo({
      curCalculator: null,
      open: false
    });
  };

  const deleteNode = (id?: string) => {
    if (!id) {
      reNewList({}, initialRow.id);
    } else {
      setIsloading(true);
      deleteIndicatorCheck(id)
        .then((res: any) => {
          if (res) {
            reNewList({}, id);
            message.success("删除配置项成功！");
          }
        })
        .finally(() => {
          setIsloading(false);
        })
        .catch((e) => {
          setIsloading(false);
        });
    }
  };

  const filterSourceTypeChange: GetProp<typeof Checkbox.Group, "onChange"> = (
    checkedValues
  ) => {
    setSourceTypeList(checkedValues);
  };

  const showFilter = () => {
    setIsShowFilter(true);
  };

  const closeFilter = () => {
    setIsShowFilter(false);
  };

  const cancleChooseSourceType = () => {
    setSourceTypeList([]);
    closeFilter();
  };

  const confirmFilterHandler = () => {
    confirmFilter();
  };

  const confirmFilter = (l?: any[]) => {
    let _list = l ? [...l] : [...list];
    if (sourceTypeList && sourceTypeList.length) {
      _list = [];
      sourceTypeList.forEach((sourceType: string) => {
        const _l = list.filter((i: any) =>
          i.sourceTypeList.includes(sourceType)
        );
        _list.push(..._l);
      });
    }
    setFilterList([..._list]);
    closeFilter();
  };

  useEffect(() => {
    fetchList();
  }, []);

  return (
    <div className="pl-5 py-4 pr-2 rounded-lg">
      <div className="h-8 leading-8 pr-3 mb-3">
        <Button
          type="primary"
          className="text-white border-0 bg-[linear-gradient(99.9deg,#2B69FF,#8F91FF)]"
          icon={<PlusCircleOutlined />}
          onClick={addRow}
        >
          新建
        </Button>
      </div>
      <div
        className="flex mr-3 bg-[#fafafa] h-12 leading-[48px] box-border min-w-[1284px] select-none"
        style={{ borderBottom: "1px solid #e4e6f8" }}
      >
        <div className="w-[18%] min-w-60 pl-4 box-border">校验项</div>
        <div className="w-[45%] min-w-[578px] pl-4 box-border">校验公式</div>
        <div className="w-[6%] min-w-20 pl-4 box-border "></div>
        <div className="w-[13%] min-w-[268px] pl-4 box-border flex justify-between">
          <span>关联表单</span>
          <Tooltip
            placement="bottomRight"
            arrow={false}
            open={isShowFilter}
            zIndex={1}
            color="white"
            styles={{
              root: {
                padding: 0
              },
              body: {
                width: "170px",
                padding: 0
              }
            }}
            title={
              <div className="text-gray-2a pt-2">
                <Checkbox.Group
                  style={{ width: "100%" }}
                  value={sourceTypeList}
                  onChange={filterSourceTypeChange}
                >
                  {sourceList.map((i: string, idx: number) => {
                    return (
                      <div
                        key={`filter-source-${i}-${idx}`}
                        className="w-full ml-3 mb-3 px-2"
                      >
                        <Checkbox
                          value={i}
                          checked={sourceTypeList.includes(i)}
                        >
                          {i}
                        </Checkbox>
                      </div>
                    );
                  })}
                </Checkbox.Group>
                <div
                  className="p-2 flex gap-2 w-[170px] box-border justify-center"
                  style={{ borderTop: "1px solid #eee" }}
                >
                  <Button
                    onClick={cancleChooseSourceType}
                    className="text-gray-2a bg-white"
                    style={{
                      border: "1px solid #dedede"
                    }}
                  >
                    取消
                  </Button>
                  <Button
                    type="primary"
                    onClick={confirmFilterHandler}
                    className="text-white border-none bg-[linear-gradient(99.9deg,#2B69FF,#8F91FF)]"
                  >
                    确认
                  </Button>
                </div>
              </div>
            }
          >
            <Button
              type="text"
              size="small"
              className={`relative top-3 w-5 h-5  hover:!text-primary-color hover:!bg-[#f1f5ff] ${
                isShowFilter || sourceTypeList.length
                  ? "text-primary-color"
                  : "text-[#bbb]"
              }`}
              icon={<FilterIcon className="mt-1" />}
              onClick={showFilter}
            />
          </Tooltip>
        </div>
        <div className="w-[18%] min-w-20 pl-4 box-border ">操作</div>
      </div>
      <Spin spinning={isLoading}>
        <div className="overflow-y-auto overflow-x-hidden mr-3 bg-white justify-center box-border min-w-[1284px] min-h-96 select-none h-[calc(100vh-260px)] ">
          {filterList && filterList.length ? (
            filterList.map((item: any, idx: number) => {
              return (
                <Item
                  key={`check-row-${item.id}-${idx}`}
                  item={item}
                  editId={editId}
                  editType={editType}
                  isLoading={isLoading}
                  rowDataChange={rowDataChange}
                />
              );
            })
          ) : (
            <Empty className="mt-32" />
          )}
        </div>
      </Spin>
      <Drawer
        destroyOnHidden={true}
        open={calculatorInfo.open}
        onClose={closeCalculatorDrawer}
        closeIcon={null}
        size={"large"}
        extra={
          <CloseOutlined
            className="cursor-pointer"
            onClick={closeCalculatorDrawer}
          />
        }
        title={`公式配置`}
        styles={{
          header: {
            height: "56px"
          },
          footer: {
            height: "72px"
          },
          body: {
            padding: "16px 20px"
          }
        }}
        footer={
          <div className="h-full flex items-center justify-end gap-[16px]">
            <Button onClick={closeCalculatorDrawer} className="text-[#2a2a2a]">
              取消
            </Button>
            <PrimaryBtn onClick={publishCaclutorsSave} loading={isLoading}>
              保存
            </PrimaryBtn>
          </div>
        }
      >
        <IndicatorEditor
          indicators={calculatorInfo.curCalculator?.calculators}
        />
      </Drawer>
    </div>
  );
};

export default Articulation;
