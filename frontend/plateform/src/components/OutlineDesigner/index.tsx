import { ConfigProvider, Form } from 'antd';
import { useCallback } from 'react';
import { DndProvider } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import OutlineItem from './OutlineItem';
import './style.css';
import { useForm } from 'antd/es/form/Form';
import { OutlineData, OutlinesDsignerProps } from './@types';

export const useOutlinesDsigner = (props: OutlinesDsignerProps) => {
  const { outlineData = [], outlinesEventEmit, limit = 3 } = props;
  const [form] = useForm();

  const handleOutlineData = useCallback(
    (outlineData: OutlineData[]) => {
      const traversalTree = (tree) => {
        return tree.map((item) => {
          if (item.children) {
            return (
              <div key={item.id}>
                <OutlineItem
                  outlinesEventEmit={outlinesEventEmit}
                  itemData={item}
                  outlineData={outlineData}
                  form={form}
                  limit={limit}
                />
                <div className="pl-[30px]">{traversalTree(item.children)}</div>
              </div>
            );
          } else {
            return (
              <OutlineItem
                outlinesEventEmit={outlinesEventEmit}
                itemData={item}
                outlineData={outlineData}
                key={item.id}
                form={form}
                limit={limit}
              />
            );
          }
        });
      };
      return outlineData.length === 1 ? (
        traversalTree(outlineData)
      ) : (
        <div className="pt-[15px]">{traversalTree(outlineData)}</div>
      );
    },
    [outlineData]
  );

  return {
    OutlineElement: (
      <>
        {!!outlineData.length && (
          <ConfigProvider
            theme={{
              token: {},
              components: {
                Form: {
                  itemMarginBottom: 0,
                },
              },
            }}
          >
            <DndProvider backend={HTML5Backend}>
              <Form form={form} className="w-full">
                {handleOutlineData(outlineData)}
              </Form>
            </DndProvider>
          </ConfigProvider>
        )}
      </>
    ),
  };
};
