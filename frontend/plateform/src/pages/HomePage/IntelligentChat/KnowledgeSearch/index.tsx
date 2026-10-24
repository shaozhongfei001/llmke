import { message, Spin } from "antd";
import { useEffect, useState, useMemo, useCallback, useRef } from "react";
import { api_getHelperConfigList } from "@/components/AiChatComparison/core/services/servers";
import { useDataTransformer } from "@/components/AiChatComparison/core/useDataTransformer";
import {
  ChatSystemType,
  StatusType,
  QAChatItem
} from "@/components/AiChatComparison/@types/sys";
import { uid } from "uid";
import { getUrlPrefix, useAppPassport } from "@/core/helps";
import AssisSelect from "./components/AssisSelect";
import SearchInput, { searchInputype } from "./components/SearchInput";
import ResultContent from "./components/ResultContentNew";
import FileList from "./components/FileListNew";
import { useAsyncEffect } from "ahooks";
import {
  api_createDialogue,
  api_start_kb_search,
  api_kbSearchHistoryList,
  api_kbSearchHistoryAdd,
  api_kbSearcHistoryDelete
} from "@/components/AiChatComparison/core/services/servers";
import IconRobot from "@/assets/svg/icon-robot.svg";
import IconTitle from "@/assets/svg/icon-title.svg";
import "@/assets/styles/knowledgeSearch.less";

const initialPage = {
  page: 1,
  pageSize: 1000
};

const cfg = {
  url: getUrlPrefix(),
  enableMock: false,
  token: "/"
};

const KnowledgeSearch = () => {
  const { getToken } = useAppPassport();
  const { assistantDTO_to_SelectOption, stremDataToQAdata } =
    useDataTransformer();
  const [assistList, setAssistList] = useState<any[]>([]);
  const [assistId, setAssistId] = useState<string>("");
  const [searchRes, setSearchRes] = useState<any>({});
  const [keyWord, setKeyWord] = useState<string>("");

  const [cfgLoading, setCfgLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isShowAssisText, setIsShowAssisText] = useState<boolean>(false);
  const [historyList, setHistoryList] = useState<Array<any>>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [isSearch, setIsSearch] = useState(false);
  const [filesObj, setFilesObj] = useState<any>({});
  const [conversation, setConversation] = useState<any>({
    id: uid(32),
    name: "",
    status: 0,
    modify_timeStamp: new Date().getTime(),
    sseController: new AbortController()
  });
  const streamDataRef = useRef<undefined | any>(undefined);
  const initMessageData = useRef<QAChatItem | undefined>(undefined);
  const [selectFile, setSelectFile] = useState<string>("");
  const [selectBlock, setSelectBlock] = useState<string>("");
  const [isHistoryHide, setIsHistoryHide] = useState<boolean>(false);
  const [clickPosition, setClickPosition] = useState<any>({ x: 0, y: 0 });
  const [isHasSearch, setIsHasSearch] = useState<boolean>(false);
  const [cptKey, setCptKey] = useState<string>(uid(32));

  const getFileName = (url: string) => {
    const regex = /([^/]+)\.([^/]+)$/;
    const match = url.match(regex);

    if (match) {
      return {
        fileName: match[1],
        fileExtension: match[2],
        url
      };
    }
    return {};
  };

  const fileList = useMemo(() => {
    const keys = Object.keys(filesObj);

    return keys.length
      ? keys.map((key: string) => {
          const obj = {
            ...getFileName(key),
            list: (filesObj[key] || []).map((i: any, idx: number) =>
              Object.assign({}, i, {
                id: `${i.order_num || i.score}_${idx}`
              })
            )
          };
          // console.log(filesObj[key])
          return obj;
        })
      : [];
  }, [filesObj]);

  const assistName = useMemo(() => {
    const item =
      assistId &&
      ["[object Number]", "[object String]"].includes(
        Object.prototype.toString.call(assistId)
      )
        ? assistList.find((i: any) => i.value === Number(assistId))
        : "";
    return item && item.label ? item.label : "";
  }, [assistId, assistList]);

  const handleAssistChanged = (aId: string) => {
    setAssistId(aId);
  };

  const getConfig = () => {
    return Object.assign({}, cfg, {
      token: getToken() || cfg.token
    });
  };

  const fetchAssisList = () => {
    setCfgLoading(true);
    api_getHelperConfigList({
      data: { ...initialPage },
      config: getConfig()
    })
      .then((res) => {
        let _records = res;
        if (Object.prototype.toString.call(_records) !== "[object Array]") {
          const { records } = res;
          _records = records || [];
        }
        const _assistId = _records && _records.length ? _records[0].id : "";
        setAssistList([...assistantDTO_to_SelectOption(_records)]);
        setAssistId(_assistId);
      })
      .finally(() => setCfgLoading(false));
  };

  const fetchHistoryList = () => {
    setHistoryLoading(true);
    api_kbSearchHistoryList({
      data: {},
      config: getConfig()
    })
      .then((res) => {
        const _list =
          Object.prototype.toString.call(res) === "[object Array]"
            ? [...res]
            : [];
        setHistoryList([...Array.from(new Set([..._list]))]);
      })
      .finally(() => {
        setHistoryLoading(false);
      });
  };

  const deleteHistory = (queryContent: string = "") => {
    api_kbSearcHistoryDelete({
      data: {
        queryContent
      },
      config: getConfig()
    }).then((res: any) => {
      if (res) {
        if (queryContent) {
          const _historyList = [...historyList];
          const idx = _historyList.findIndex((i: string) => i === queryContent);
          _historyList.splice(idx, 1);
          setHistoryList([..._historyList]);
        } else {
          setHistoryList([]);
        }
      }
    });
  };

  const keyOnChange = (val: string, isSearch: boolean = false) => {
    setKeyWord(val);
    if (isSearch) {
      setTimeout(() => {
        keyOnSearch(val);
      }, 0);
    }
  };

  const keyOnSearch = (val?: string) => {
    const _val = val || keyWord;
    if (_val) {
      setConversation({
        ...conversation,
        status: StatusType.Process,
        question: _val
      });
      api_kbSearchHistoryAdd({
        data: {
          queryContent: _val
        },
        config: getConfig()
      }).then(() => {
        setHistoryList([...Array.from(new Set([...historyList, _val]))]);
      });
    }
  };

  const onBlurHandler = () => {
    setTimeout(() => {
      isShowAssisText && setIsShowAssisText(false);
    }, 500);
  };

  const showAssisText = () => {
    !isShowAssisText && setIsShowAssisText(true);
  };

  const fixRetrieveTag = (content: string) => {
    return Object.prototype.toString.call(content) === "[object String]"
      ? content.replace(/\[retrive-tag[^\]]*\].*?\[\/retrive-tag\]/g, "")
      : content;
  };

  const onMessageCallback = useCallback((event: any) => {
    const curData = JSON.parse(event.data);
    // console.log(curData, StatusType.Done)
    setConversation({
      ...conversation,
      status: curData.status
    });
    if (curData.status === StatusType.Done) {
      const { docsTree } = curData;
      if (docsTree) {
        try {
          setFilesObj(JSON.parse(docsTree));
        } catch (e) {
          console.log(e);
        }
      }
      setIsSearch(false);
      setSearchRes((prevChat: any) => {
        streamDataRef.current =
          streamDataRef.current || initMessageData.current;
        if (streamDataRef.current) {
          const lastData = { ...curData };
          lastData.reply.content =
            streamDataRef.current?.answer?.content + curData.reply.content ||
            "";
          const data = stremDataToQAdata(lastData);
          // console.log("最新对话的最终处理数据", data)
          const p = {
            ...streamDataRef.current,
            answer: {
              ...streamDataRef.current.answer,
              id: data?.qaData?.id || "",
              reference: data?.qaData?.answer?.reference || [],
              content: fixRetrieveTag(lastData.reply.content),
              type: "text"
            },
            status: StatusType.Done
          };
          // console.log("最新对话的最终数据", p)
          streamDataRef.current = undefined;
          return { ...p };
        }
        return prevChat;
      });
    } else {
      streamDataRef.current = !streamDataRef.current
        ? initMessageData.current
        : {
            ...streamDataRef.current,
            answer: {
              ...(curData.reply || {}),
              content:
                streamDataRef.current.answer.content +
                (curData.reply.content || ""),
              type: "text" // 修正类型
            }
          };
      try {
        setSearchRes((prevChat: any) => {
          if (streamDataRef.current) {
            const lastData = { ...curData };
            lastData.reply.content =
              streamDataRef.current?.answer?.content || "";
            const data = stremDataToQAdata(lastData);
            if (streamDataRef.current?.answer?.reference) {
              streamDataRef.current.answer.reference =
                data?.qaData?.answer?.reference || [];
              streamDataRef.current.answer.id = data?.qaData?.id || "";
            }
            // console.log("data :", data)
            const p = {
              ...streamDataRef.current,
              status: StatusType.Process
            };
            return { ...p };
          }
          return prevChat;
        });
      } catch (e) {
        console.error(e);
      }
    }
  }, []);

  const onErrorCallback = useCallback(
    (e: any) => {
      setIsSearch(false);
      setConversation({
        ...conversation,
        status: StatusType.Done
      });

      setSearchRes((prevChat: any) => {
        const p = {
          ...(streamDataRef.current || initMessageData.current),
          status: StatusType.Done
        };
        streamDataRef.current = undefined;
        return { ...p };
      });
      message.error("请求失败!");
      throw e;
    },
    [conversation]
  );

  const onCloseCallback = useCallback(() => {
    setIsSearch(false);
    // console.log("onCloseCallback sse")
    // console.log("这里已经关闭了，不应该有数据")
    conversation?.sseController.abort();
  }, [conversation]);

  const resetAll = () => {
    setIsSearch(true);
    setSearchRes({});
    setFilesObj({});
    clearSelect();
  };

  const clearSelect = () => {
    setSelectBlock("");
    setSelectFile("");
  };

  const selectFileHandler = (fileId: string) => {
    setSelectFile(fileId);
    setSelectBlock("");
  };

  const selectBlockHandler = (blockId: string) => {
    setSelectBlock(blockId);
  };

  const historyHideHandler = (sta: boolean) => {
    if (sta !== isHistoryHide) {
      setIsHistoryHide(sta);
      setTimeout(() => {
        setIsHistoryHide(!sta);
      }, 10);
    }
  };

  const containerClickHandler = (e: any) => {
    // e.preventDefault()
    // e.stopPropagation()
    if (!isHasSearch) {
      const { clientX, clientY } = e;
      // console.log(e.target, clientX, clientY)
      setClickPosition({
        x: clientX,
        y: clientY
      });
    }
  };

  const resetClickPosition = (data: any) => {
    setClickPosition({ ...data });
  };

  useAsyncEffect(async () => {
    if (
      conversation &&
      conversation.status === StatusType.Process &&
      conversation?.question &&
      keyWord
    ) {
      resetAll();
      const dialogId = `${uid(32)}_${assistId}`;
      const res = await api_createDialogue({
        data: {
          label: keyWord,
          sessionId: dialogId,
          assist_id: assistId!,
          sysType: ChatSystemType.TEMPORARY
        },
        config: getConfig()
      });

      if (res && conversation.status === StatusType.Process) {
        conversation.sseController = new AbortController();
        const chat_id = uid(32);
        const serverInfo = getConfig();
        conversation?.sseController.abort();
        api_start_kb_search({
          data: {
            sessionId: res.sessionId,
            queryId: chat_id,
            name: res.name,
            lastDate: new Date().getTime().toString(),
            type: "text",
            content: keyWord,
            configId: res.configId,
            audioUrl: "",
            onMessage: onMessageCallback,
            onError: onErrorCallback,
            onClose: onCloseCallback,
            signal: conversation.sseController.signal
          },
          config: {
            url: serverInfo.url,
            token: serverInfo.token,
            enableMock: false
          }
        });
      }
      const p: QAChatItem = {
        id: res ? res.sessionId : dialogId!,
        query: {
          content: keyWord!,
          type: "text",
          audioUrl: "",
          queryId: uid(32)
        },
        answer: {
          content: ""
        },
        status: StatusType.Pending,
        searchConfigDTO: res ? res.searchConfigDTO : undefined // 添加此行以解决错误
      };
      initMessageData.current = p;
      if (!isHasSearch) {
        setIsHasSearch(true);
      }
      setCptKey(uid(32));
      setSearchRes((prevChat: any) => {
        return { ...prevChat, ...p };
      });
    }
  }, [conversation]);

  useEffect(() => {
    fetchAssisList();
    fetchHistoryList();
  }, []);

  return (
    <div
      className="knowledge-search-wrap p-5 mb-10 pr-0"
      onClick={containerClickHandler}
    >
      <Spin spinning={loading}>
        <div className="flex h-12 pr-5">
          {isHasSearch ? (
            <div className="flex-1 pr-5 search-wrap">
              <SearchInput
                loading={false}
                keyWord={keyWord}
                historyList={historyList}
                historyLoading={historyLoading}
                isSearch={isSearch}
                isHistoryHide={isHistoryHide}
                keyOnChange={keyOnChange}
                keyOnSearch={keyOnSearch}
                deleteHistory={deleteHistory}
              />
            </div>
          ) : null}
          <div className="min-w-[448px] w-1/3">
            {isHasSearch ? (
              <AssisSelect
                disabled={false}
                assistList={assistList}
                value={assistId || ""}
                loading={cfgLoading}
                onChange={handleAssistChanged}
              />
            ) : (
              <div
                className={`show-search-select-wrap`}
                onFocus={showAssisText}
              >
                <div className="select-wrap">
                  <AssisSelect
                    disabled={false}
                    assistList={assistList}
                    value={assistId || ""}
                    loading={cfgLoading}
                    onChange={handleAssistChanged}
                    onBlurHandler={onBlurHandler}
                  />
                </div>
                {/* <div className="flex"> */}
                {/* <div className="select-value-wrap relative flex">
                  <img src={IconRobot} />
                  {assistName}
                </div> */}
              </div>
            )}
          </div>
        </div>
        {!isHasSearch ? (
          <div className="w-full h-[calc(100vh-130px)] min-h-96 flex justify-center mt-12">
            <div className="w-2/3 search-wrap max-w-[1000px]">
              <div className=" text-center mb-3">
                <img src={IconTitle} className="inline-block" />
              </div>
              <div className="desc-wrap text-center text-sm text-[#888] mb-6">
                智能检索，多元信源，精准解答
              </div>
              <SearchInput
                type={searchInputype.LARGE}
                loading={false}
                keyWord={keyWord}
                historyList={historyList}
                historyLoading={historyLoading}
                isSearch={isSearch}
                isHistoryHide={isHistoryHide}
                clickPosition={clickPosition}
                keyOnChange={keyOnChange}
                keyOnSearch={keyOnSearch}
                deleteHistory={deleteHistory}
                resetClickPosition={resetClickPosition}
              />
              <div className="flex justify-center items-center mb-4"></div>
              <div className="flex flex-wrap text-sm  text-gray-500  gap-2 mt-4">
                <div
                  onClick={() => {
                    setKeyWord("你好，你是谁");
                    keyOnSearch("你好，你是谁");
                  }}
                  className="px-5 py-2 rounded border border-gray-300 bg-white  text-sm cursor-pointer hover:border-gray-500 transition-all mr-2 mb-2 select-none"
                >
                  你好，你是谁
                </div>
                <div
                  onClick={() => {
                    setKeyWord("地下钱庄身份信息的识别点的团伙特征是什么");
                    keyOnSearch("地下钱庄身份信息的识别点的团伙特征是什么");
                  }}
                  className="px-5 py-2 rounded border border-gray-300 bg-white  text-sm cursor-pointer hover:border-gray-500 transition-all mr-2 mb-2 select-none"
                >
                  地下钱庄身份信息的识别点的团伙特征是什么
                </div>
                <div
                  onClick={() => {
                    setKeyWord("如何取消原先预订的酒店再重新定");
                    keyOnSearch("如何取消原先预订的酒店再重新定");
                  }}
                  className="px-5 py-2 rounded border border-gray-300 bg-white  text-sm cursor-pointer hover:border-gray-500 transition-all mr-2 mb-2 select-none"
                >
                  如何取消原先预订的酒店再重新定
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="result-wrap">
            <ResultContent
              answer={searchRes.answer}
              status={conversation.status}
              selectFile={selectFile}
              selectBlock={selectBlock}
              isHistoryHide={isHistoryHide}
              fileList={fileList}
              historyHideHandler={historyHideHandler}
              clearSelect={clearSelect}
            />
            <FileList
              key={`file-list-${cptKey}`}
              fileList={fileList}
              selectFile={selectFile}
              selectBlock={selectBlock}
              selectFileHandler={selectFileHandler}
              selectBlockHandler={selectBlockHandler}
            />
          </div>
        )}
      </Spin>
    </div>
  );
};

export default KnowledgeSearch;
