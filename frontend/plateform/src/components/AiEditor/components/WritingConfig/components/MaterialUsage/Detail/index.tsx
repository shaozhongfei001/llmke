import { Button, Checkbox, CheckboxChangeEvent, Select } from "antd";
import ItemName from "../../ItemName";

interface Iprops {
  item: any;
  setList: any;
  handleDel: (item: any) => any;
}

export const Detail = ({ item, setList, handleDel }: Iprops) => {
  const handleSelect = (value: string) => {
    setList((list: any) => {
      return list.map((i: any) => {
        return {
          ...i,
          usage: item.customId === i.customId ? value : i.usage
        };
      });
    });
  };

  const handleCheck = (e: CheckboxChangeEvent) => {
    const _check = e.target.checked;
    setList((list: any) => {
      return list.map((i: any) => {
        return {
          ...i,
          checkboxValue: item.customId === i.customId ? _check : i.checkboxValue
        };
      });
    });
  };

  return (
    <div
      className="flex items-center h-[54px] box-border pl-[16px] justify-between"
      style={{
        borderBottom: "1px solid #eee",
        width: "952px"
      }}
    >
      <div className="flex h-full">
        <Checkbox
          className="mr-[32px]"
          checked={item.checkboxValue}
          onChange={handleCheck}
        />
        <div className="w-[522px]">
          <ItemName item={item}></ItemName>
        </div>
      </div>
      <div className="w-[235px] h-[24px] flex items-center justify-between">
        <Select
          className="w-[175px]"
          value={item.usage}
          options={[
            { value: "content", label: "切片检索" },
            {
              value: "template",
              label: "全文引用"
              // disabled: item.refEntityType !== "document"
            },
            {
              value: "both",
              label: "全部来源"
              // disabled: item.refEntityType !== "document"
            }
          ]}
          onChange={handleSelect}
        />
        <Button type="link" onClick={(_) => handleDel(item)}>
          删除
        </Button>
      </div>
    </div>
  );
};

export default Detail;
