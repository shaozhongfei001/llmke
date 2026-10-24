import { useState, useMemo, useEffect, useRef } from "react";
import { Select, Checkbox, Input } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { OutlineType } from "../type.ts";

interface MaterialSelectype {
  record: any;
  options: Array<any>;
  relations: any;
  findMaterialItemById: (id: number) => any;
  selectMaterials: (
    selValues: any[],
    record: OutlineType,
    material: any
  ) => void;
}

const MaterialSelect = (props: MaterialSelectype) => {
  const { record, options, relations, findMaterialItemById, selectMaterials } =
    props;
  const { children, relatedMaterials, section } = record;
  const [selectValues, setSelectValues] = useState<any>({});
  const selectValuesRef = useRef<any>({});
  const [searchVal, setSearchVal] = useState<string>("");

  const materialOptions = useMemo(() => {
    return searchVal
      ? (options || []).filter((i: any) => i.label.indexOf(searchVal) >= 0)
      : options;
  }, [searchVal, options]);

  const getCheckedList = (key: string) => {
    return searchVal
      ? (selectValuesRef.current[key] || []).filter(
          (i: any) => i.label.indexOf(searchVal) >= 0
        )
      : selectValuesRef.current[key];
  };

  // const relations = useMemo(() => {
  //   const obj = {} as any;
  //   if (relatedMaterials) {
  //     const entriesArray = Array.from(relatedMaterials.entries()) as any;
  //     entriesArray.forEach(([key, value]: [key: number, value: Array<any>]) => {
  //       obj[key] = [...value];
  //     });
  //   }
  //   return JSON.parse(JSON.stringify(obj));
  // }, [relatedMaterials]);

  const getMaxTagTextLength = (len: number) => {
    return len <= 1 ? 21 : 9;
  };

  const selectValueOnChange = (
    key: string,
    values: Array<any>,
    record: any
  ) => {
    selectValuesRef.current = {
      ...selectValuesRef.current,
      [key]: [...values],
    };

    setSelectValues({
      ...selectValuesRef.current,
      [key]: [...values],
    });
    selectMaterials(values, record, key);
  };

  const searchChangeHandler = (e: any) => {
    const { target } = e;
    setSearchVal(target.value.trim() || "");
  };

  const dropdownRender = (menu: any, record: OutlineType, key: any) => {
    const onCheckAllChange = (target: any, record: OutlineType, key: any) => {
      const { checked } = target;
      const checkedList = selectValuesRef.current[key] || [];

      const _addItems = JSON.parse(JSON.stringify(materialOptions));
      const _oldItems = searchVal
        ? checkedList.filter((i: any) => i.label.indexOf(searchVal) < 0)
        : [];

      const items = checked ? _addItems.concat(_oldItems) : _oldItems;
      selectValueOnChange(key, [...items], record);
    };

    const len = getCheckedList(key)?.length;

    return (
      <>
        <div className="ml-1">
          <Input
            placeholder="输入名称搜索"
            prefix={<SearchOutlined className="text-[#bbb] text-lg" />}
            className="text-sm text-[#bbb] border-solid border-[#d9d9d9]"
            value={searchVal}
            onChange={searchChangeHandler}
            onKeyDown={(e) => e.stopPropagation()}
          />
        </div>
        <div className="ml-1 mb-1 pt-1">
          <Checkbox
            disabled={materialOptions.length === 0}
            indeterminate={len > 0 && len < materialOptions.length}
            checked={!!len && len === materialOptions.length}
            onChange={(e) => {
              onCheckAllChange(e.target, record, key);
            }}
          >
            全部
          </Checkbox>
        </div>
        {menu}
      </>
    );
  };

  const isChecked = (key: string, option: any) => {
    return (
      option.value &&
      (selectValues[key] || [])
        .map((i: any) => i.value)
        .includes(Number(option.value))
    );
  };

  useEffect(() => {
    if (relations && Object.keys(relations).length) {
      const obj = {} as any;
      Object.keys(relations).forEach((key: string) => {
        obj[key] = relations[key].map((li: any) => {
          return {
            label: li.fileName,
            value: Number(li.fileId),
          };
        });
      });
      selectValuesRef.current = {
        ...selectValuesRef.current,
        ...obj,
      };
      setSelectValues({ ...obj });
    }
  }, [relations]);

  return (
    <div
      className={`${children && children.length > 0 ? "col-2 " : ""}relateMaterials`}
    >
      {(section?.materialType || []).map((key: string) => {
        const m = findMaterialItemById(Number(key));
        if (!m || !m.name) {
          return null;
        }
        return (
          <>
            {/* <div>
              {JSON.stringify(m)}---{JSON.stringify(selectValues)}
            </div> */}
            <Select
              key={key}
              style={{
                width: "286px",
                marginLeft: "6px",
                marginBottom: "6px",
              }}
              mode="multiple"
              showSearch={false}
              labelInValue
              placeholder={m.name || "请选择"}
              value={selectValues[key]}
              defaultValue={selectValues[key]}
              maxTagCount={1}
              maxTagTextLength={getMaxTagTextLength(selectValues[key]?.length)}
              onChange={(values: Array<any>) => {
                selectValueOnChange(key, values, record);
              }}
              dropdownRender={(menu) => dropdownRender(menu, record, key)}
              options={materialOptions}
              optionRender={(option) => (
                <div key={option.value} className="material-option">
                  <Checkbox className="mr-3" checked={isChecked(key, option)} />
                  {option.label}
                </div>
              )}
            ></Select>
          </>
        );
      })}
    </div>
  );
};
export default MaterialSelect;
