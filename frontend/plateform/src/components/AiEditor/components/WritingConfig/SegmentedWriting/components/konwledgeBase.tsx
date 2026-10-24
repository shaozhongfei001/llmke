import { useMemo, memo } from "react";
import { Select } from "antd";
import { v4 as uuid } from "uuid";
import { OutlineType } from "../type.ts";
const SelectKnowledgeBase = ({
  id,
  knowledge_base,
  options,
  setOutlines
}: any) => {
  const getMaxTagTextLength = (len: number) => {
    return len <= 1 ? 21 : 9;
  };
  console.log("-------reder kk");
  const selValue = useMemo(() => {
    if (knowledge_base?.length > 0) {
      return knowledge_base[0].refIds.map((id: any, index: number) => {
        return {
          label: knowledge_base[0].refNames[index],
          value: id
        };
      });
    }
    return [];
  }, [knowledge_base]);

  const selectKonwledgeBase = (value: any) => {
    const knowledge: {
      sourceType: "knowledge_base";
      refIds: any[];
      refNames: string[];
    } = {
      sourceType: "knowledge_base",
      refIds: [],
      refNames: []
    };
    value.forEach((v: any) => {
      knowledge.refIds.push(v.value);
      knowledge.refNames.push(v.label);
    });

    setOutlines((pre: OutlineType[]) => {
      const newOutLines = [...pre];
      function traverse(paragraphs: OutlineType[]) {
        paragraphs.forEach((p: OutlineType) => {
          if (p.id == id) {
            p.contentSources = [...(p.contentSources || [])];
            const index = p.contentSources?.findIndex(
              (c) => c.sourceType == "knowledge_base"
            );
            if (value?.length > 0) {
              if (index !== -1) {
                p.contentSources.splice(index, 1, knowledge);
              } else {
                p.contentSources.push(knowledge);
              }
            } else {
              if (index !== -1) {
                p.contentSources.splice(index, 1);
              }
            }
          }

          // 如果有子段落，递归调用
          if (p.children) {
            traverse(p.children);
          }
        });
      }
      traverse(newOutLines);
      return newOutLines;
    });
  };

  return (
    <Select
      key={uuid()}
      style={{
        width: "286px",
        marginLeft: "6px",
        marginBottom: "6px"
      }}
      mode="multiple"
      labelInValue
      placeholder="请选择知识库"
      options={options || []}
      value={selValue}
      maxTagCount={1}
      maxTagTextLength={getMaxTagTextLength(selValue.length)}
      onChange={(value) => selectKonwledgeBase(value)}
    />
  );
};

export default memo(SelectKnowledgeBase);
