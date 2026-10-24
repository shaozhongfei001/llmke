import VirtualList from "rc-virtual-list";
import { debounce } from "lodash";
import React, { useState, useEffect, useRef } from "react";

type T = {
  clientHeight: number;
  current: HTMLDivElement | null;
};

export interface IVirtualWrap {
  className?: string;
  list: Array<any>;
  paddingY: number;
  itemHeight: number;
  wrapPadding: number;
  children: React.ReactNode;
  wrapperRef: React.RefObject<T>;
  itemKey?: string;
  onClick?: (row: any) => void;
}

const VirtualWrap: React.FC<IVirtualWrap> = (props) => {
  const {
    list,
    itemHeight,
    paddingY,
    wrapPadding,
    children,
    itemKey,
    wrapperRef,
    onClick
  } = props;
  const [containerHeight, setContainerHeight] = useState<number>();
  const pageSizeRef = useRef(0);
  const [data, setData] = useState<any[]>([]);

  const appendData = () => {
    if (list && (list.length || list.length === 0)) {
      const len = data.length;
      const max = list.length;
      const _end = len + pageSizeRef.current;
      const end = _end > max ? max : _end;
      if (end > len) {
        const newData = list.slice(len, end);
        setData([...data, ...newData]);
      }
    }
  };

  const initData = () => {
    if (wrapperRef && wrapperRef.current && wrapperRef.current.clientHeight) {
      const { clientHeight } = wrapperRef.current;
      const _pageSize =
        Math.ceil((clientHeight - wrapPadding) / (itemHeight + paddingY)) + 5;
      setContainerHeight(clientHeight);
      pageSizeRef.current = _pageSize;
      appendData();
    }
  };

  const resizeFn = debounce(() => {
    initData();
  }, 500);

  useEffect(() => {
    window.addEventListener("resize", resizeFn);
    return () => {
      window.removeEventListener("resize", resizeFn);
    };
  }, []);

  useEffect(() => {
    initData();
  }, [wrapperRef, list]);

  const rowClick = (row: any) => {
    onClick && onClick(row);
  };

  return (
    <>
      {list && list.length && data.length ? (
        <VirtualList
          data={list}
          height={
            containerHeight && containerHeight > wrapPadding
              ? containerHeight - wrapPadding
              : containerHeight
          }
          itemHeight={itemHeight + paddingY}
          itemKey={itemKey || "id"}
        >
          {(item: any, index: number) => (
            <div
              className="p-0"
              key={
                itemKey && item.length
                  ? `virtual-row-${item[0][itemKey]}`
                  : Object.prototype.toString.call(item) === "[object String]"
                    ? JSON.stringify(item)
                    : index
              }
              onClick={() => {
                rowClick(item);
              }}
            >
              {React.Children.map(children, (child) => {
                if (!React.isValidElement(child)) {
                  return null;
                }
                return React.cloneElement(child, {
                  ...child.props,
                  key: `item_${index}`,
                  item
                });
              })}
            </div>
          )}
        </VirtualList>
      ) : null}
    </>
  );
};

export default VirtualWrap;
