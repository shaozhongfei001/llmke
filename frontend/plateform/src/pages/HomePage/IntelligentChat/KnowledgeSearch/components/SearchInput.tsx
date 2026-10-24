import React, {
  useState,
  useMemo,
  useCallback,
  useEffect,
  useRef
} from "react";
import { Input, Spin } from "antd";

import IconHistory from "@/assets/svg/Icon-history.svg";
import IconSearch from "@/assets/svg/icon-zoomOut.svg";
import IconStar from "@/assets/svg/icon-search-bar.svg";
import { DeleteOutlined, SearchOutlined } from "@ant-design/icons";

import "./new-style.less";

export enum searchInputype {
  NORMAL = "normal",
  LARGE = "large"
}

interface SearchInputProps {
  type?: searchInputype;
  placeholder?: string;
  loading: boolean;
  keyWord: string;
  historyList: Array<any>;
  historyLoading: boolean;
  isSearch: boolean;
  isHistoryHide: boolean;
  clickPosition?: any;
  keyOnChange: (val: string, isSearch?: boolean) => void;
  keyOnSearch: () => void;
  deleteHistory: (content: string) => void;
  resetClickPosition?: (data: any) => void;
}

const SearchInput: React.FC<SearchInputProps> = ({
  type = searchInputype.NORMAL,
  placeholder = "智能提问，AI高效搜索",
  loading,
  keyWord,
  historyList,
  historyLoading,
  isSearch,
  isHistoryHide,
  clickPosition,
  keyOnChange,
  keyOnSearch,
  deleteHistory,
  resetClickPosition
}) => {
  const [isFocus, setIsFocus] = useState<boolean>(false);
  const iptRef = useRef<any>(null);

  const historyFilterList = useMemo(() => {
    return keyWord
      ? (historyList || []).filter((i: any) => i.includes(keyWord))
      : historyList;
  }, [historyList, keyWord]);

  const keyWordOnChange = (e: any) => {
    const { target } = e;
    keyOnChange(target.value.trim());
  };

  const keyWordOnKeyDown = (e: any) => {
    const { key, keyCode } = e;
    if (key === "Enter" || keyCode === 13) {
      searchHandler();
    }
  };

  const searchHandler = () => {
    if (keyWord) {
      keyOnSearch();
      console.log(iptRef.current);
      iptRef.current && iptRef.current.blur && iptRef.current.blur();
    }
  };

  const onFocusHandler = () => {
    !isFocus && setIsFocus(true);
  };

  const onblurHandler = () => {
    // setIsFocus(false);
  };

  const maskOnClick = () => {
    setIsFocus(false);
  };

  const deleteAllHistory = () => {
    deleteHistory("");
  };

  const deleteRowHandler = useCallback(
    (item: any) => (e: any) => {
      e.stopPropagation();
      console.log(item);
      deleteHistory(item);
    },
    [deleteHistory]
  );

  const selectRowHandler = useCallback(
    (item: any) => () => {
      keyOnChange(item, true);
      setIsFocus(false);
    },
    [keyOnChange, setIsFocus]
  );

  const checkIfCloseHistory = () => {
    const defaultPosition = { x: 0, y: 0, width: 0, height: 0 };
    const searchIptEl = document.querySelector(".select-input-large");
    const historyEl = document.querySelector(".history-wrap");
    const searchIptClientRect = searchIptEl
      ? searchIptEl.getBoundingClientRect()
      : { ...defaultPosition };
    const historyClientRect = historyEl
      ? historyEl.getBoundingClientRect()
      : { ...defaultPosition };

    const xList = [
      searchIptClientRect.x,
      searchIptClientRect.x + searchIptClientRect.width
    ];
    const yList = [
      searchIptClientRect.y,
      searchIptClientRect.y +
        searchIptClientRect.height +
        15 +
        historyClientRect.height
    ];
    if (
      !(
        clickPosition.x > xList[0] &&
        clickPosition.x < xList[1] &&
        clickPosition.y > yList[0] &&
        clickPosition.y < yList[1]
      )
    ) {
      isFocus && setIsFocus(false);
    } else {
      !isFocus && setIsFocus(true);
    }
  };

  const renewClickPosition = (e: any) => {
    console.log(e.clientX, e.clientY);
    // e.preventDefault()
    // e.stopPropagation()
    resetClickPosition && resetClickPosition({ x: e.clientX, y: e.clientY });
  };

  useEffect(() => {
    if (isSearch || isHistoryHide) {
      setIsFocus(false);
    }
  }, [isSearch, isHistoryHide]);

  useEffect(() => {
    if (clickPosition && (clickPosition.x || clickPosition.y)) {
      checkIfCloseHistory();
    }
  }, [clickPosition]);

  return (
    <div
      className={`w-full relative select-input-${type === searchInputype.NORMAL ? "normal" : "large"} ${isFocus ? "select-input-focus" : ""} bg-white z-50`}
      onClick={renewClickPosition}
    >
      <i className="icon-start">
        <img src={IconStar} />
      </i>
      <Input
        ref={iptRef}
        placeholder={placeholder}
        disabled={loading}
        value={keyWord}
        onChange={keyWordOnChange}
        onKeyDown={keyWordOnKeyDown}
        onFocus={onFocusHandler}
        onBlur={onblurHandler}
      />
      <b>
        <img src={IconSearch} onClick={searchHandler} />
      </b>
      <div className="mask-line"></div>
      <div className={`${isFocus ? "block" : "hidden"} history-wrap`}>
        {/* <div className={`history-wrap`}> */}
        <div className="history-list-wrap">
          <div className="flex mb-3 justify-between">
            <div className="">搜索历史</div>
            <div
              className={`clear-wrap ${historyFilterList.length === 0 ? "cursor-not-allowed" : "cursor-pointer"}`}
              onClick={deleteAllHistory}
            >
              <DeleteOutlined className={`mr-1 text-[#888]`} />
              清空
            </div>
          </div>
          <Spin spinning={historyLoading}>
            {historyFilterList.map((i: any, idx: number) => {
              return (
                <div
                  key={`history-row-${idx}`}
                  className="history-row"
                  onClick={selectRowHandler(i)}
                >
                  {!keyWord ? (
                    <img src={IconHistory} className="history-icon" />
                  ) : (
                    <SearchOutlined className="search-icon" />
                  )}
                  <span>{i}</span>
                  <b onClick={deleteRowHandler(i)}></b>
                </div>
              );
            })}
            {historyFilterList.length == 0 ? (
              <div className="text-center">暂无结果</div>
            ) : null}
          </Spin>
        </div>
      </div>
    </div>
  );
};

export default SearchInput;
