import { GientechChat } from "@mxmweb/aichat";
import {
  dealMinioUrl,
  downloadByStream,
  FILEIMG,
  fileViewTypes,
  getFileName,
  getMarkExcludeType,
  handleDownLoad,
  TempBaseUrl,
  useAppPassport
} from "@root/src/core/helps";
import { useMemo, useState } from "react";
import { ConfigProvider, Drawer, message } from "antd";
import { DeleteModal } from "./components/DeleteModal";
import SdqaDrawer from "@root/src/components/SdqaDrawer";
import { RenameModal } from "./components/RenameModal";
import { DrawerContent } from "./components/DrawerContent";
import DrawerPreview from "./components/DrawerPreview";
import { defaultStyles } from "./config";

const ChatPage = () => {
  const { getToken } = useAppPassport();
  const token: any = getToken();
  const AI_CHAT = useMemo(() => {
    return GientechChat();
  }, []);
  const [isRenameModalOpen, setisRenameModalOpen] = useState(false);
  const [isRemoveModalOpen, setisRemoveModalOpen] = useState(false);
  const [curEditData, setCurEditData] = useState<any>(null);
  const [sdDrawerOpen, setSdDrawerOpen] = useState(false);
  const [drawerData, setDrawerData]: any = useState({});
  const [open, setOpen] = useState(false);
  const [content, setContent] = useState<
    | {
        title: "";
        file_type: "";
        metadata: { offset: [] };
      }
    | any
  >(null);
  const [drawerType, setDrawerType] = useState<string>("mark");
  const [curFileInfo, setCurFileInfo] = useState({
    url: "",
    parse_url: "",
    file_type: "",
    file_name: ""
  });
  const editDialog = (data: any) => {
    const newLabel = data.new_name;
    const oldLabel = curEditData.data.label;
    if (newLabel && newLabel !== oldLabel) {
      curEditData
        .async_renameConversation(newLabel)
        .then(() => {
          curEditData.fn_renameItemInList(newLabel);
          setisRenameModalOpen(false);
        })
        .catch(() => {
          // 重命名失败
        });
    } else {
      setisRenameModalOpen(false);
    }
  };

  const editRemove = (data: any) => {
    curEditData
      .async_deleteConversation()
      .then(() => {
        curEditData.fn_removeItemFromList();
        setisRemoveModalOpen(false);
      })
      .catch(() => {
        // 删除失败
      });
  };

  const handleSd = (type: string, data?: any) => {
    switch (type) {
      case "click:indexes":
        setOpen(true);
        setContent(data);
        break;
      case "open":
        setDrawerData(data);
        setSdDrawerOpen(true);
        break;
      case "close":
        setSdDrawerOpen(false);
        break;
    }
  };

  const handleEvent = (type: string, data?: any) => {
    console.log(type, data);

    switch (type) {
      case "close_remove":
        setisRemoveModalOpen(false);
        break;
      case "close_rename":
        setisRenameModalOpen(false);
        break;
      case "ok_rename":
        editDialog(data);
        break;
      case "ok_remove":
        editRemove(data);
        break;
    }
  };

  return (
    <>
      <div className="h-full">
        <AI_CHAT
          token={token}
          url={"/proxy"}
          CustomComponents={{
            LogoBox: null
          }}
          styles={defaultStyles}
          eventsEmit={(event: any, data: any) => {
            console.log("事件触发:", event, data);
            switch (event) {
              case "conversations:rename_icon_clicked":
                setCurEditData(data);
                setisRenameModalOpen(true);
                break;
              case "conversations:delete_icon_clicked":
                setCurEditData(data);
                setisRemoveModalOpen(true);
                break;
              case "referenceFile_download":
                const d1 = data.data;
                downloadByStream({
                  filePath: `${TempBaseUrl}${d1.metadata.source}`,
                  fileName: getFileName(d1)
                });

                break;
              case "referenceFile_question":
              case "referenceFile_view":
                const d2 = data.data;
                setCurFileInfo({
                  ...d2,
                  url: fileViewTypes.includes(d2.file_type)
                    ? d2.metadata.source
                      ? `${TempBaseUrl}${d2.metadata.source}`
                      : d2.parsedFilePath || d2.convertedFilePath
                    : d2.parsedFilePath || d2.convertedFilePath
                });

                setDrawerType("preview");
                setOpen(true);
                break;
              case "reference_file:click":
                // if(data.file_type === 'database' || data.file_type === 'image')return
                // if (!data.url && !data.parse_url) {
                //   return message.warning("该文件未解析完成，请稍后再试");
                // }
                // setCurFileInfo({
                //   ...data,
                //   file_type: data.type,
                //   file_name: data.file
                // });
                // setDrawerType("preview");
                // setOpen(true);
                break;

              case "knowledge_referenceFile_title:click":
                const d = data.data;
                if (d.isUploadFile) {
                  setDrawerData({
                    ...d,
                    file_source: d.parsedFilePath,
                    file_type: d.type
                  });
                } else {
                  setDrawerData({ ...d, file_source: d.parsedFilePath });
                }
                setDrawerType("preview");
                setSdDrawerOpen(true);
                break;
              case "action_retrive_tag":
              case "retrive_tag:click":
                if (!data?.tagInfo && !data?.file) return;
                const curFile = data?.tagInfo || data?.file;
                const { pdfPages, parsedFilePath, order_num, metadata } =
                  curFile;
                const id = curFile.id || order_num || "Unknown ID";
                // 解析 source 字段
                const sourceParts = metadata.source.split("/");
                const fileName = sourceParts[sourceParts.length - 1] || "";
                const fileParts = fileName.split(".");
                const label =
                  fileParts.slice(0, -1).join(".") || "Unknown Label";
                const file_type =
                  fileParts[fileParts.length - 1] || "Unknown Type";

                setContent({
                  id,
                  title: label,
                  file_name: fileName,
                  file_type: file_type,
                  file_source: getMarkExcludeType(file_type)
                    ? `${TempBaseUrl}${metadata.source}`
                    : parsedFilePath,
                  metadata: metadata,
                  pdfPages: pdfPages
                });
                setDrawerType("mark");
                setOpen(true);
                break;
            }

            // 监听所有交互事件
          }}
        />
      </div>
      <RenameModal
        isModalOpen={isRenameModalOpen}
        handleOk={handleEvent}
        handleCancel={() => handleEvent("close_rename")}
        data={curEditData?.data || {}}
      />
      <DeleteModal
        isModalOpen={isRemoveModalOpen}
        handleOk={handleEvent}
        handleCancel={() => handleEvent("close_remove")}
        data={curEditData?.data || {}}
      />
      <SdqaDrawer
        open={sdDrawerOpen}
        title={drawerData.file_name}
        close={() => handleSd("close")}
        content={drawerData}
        setContent={setDrawerData}
        is_download={true}
      />
      <ConfigProvider
        drawer={{
          styles: {
            body: { padding: 0 },
            header: { display: "none" }
          }
        }}
      >
        <Drawer
          title={
            <div className="flex items-center">
              <img
                src={FILEIMG[content?.file_type || "doc"]}
                width={18}
                height={18}
                className="mr-[6px]"
              />
              <div>{`${content?.title}.${content?.file_type}`}</div>
            </div>
          }
          autoFocus={false}
          onClose={() => setOpen(false)}
          open={open}
          width={600}
          className="overflow-x-hidden"
          destroyOnClose
          afterOpenChange={(open) => {
            if (!open) {
              setContent(null);
            }
          }}
        >
          {drawerType === "mark" ? (
            <DrawerContent
              content={content as any}
              onClose={() => setOpen(false)}
            />
          ) : (
            <DrawerPreview
              curFileInfo={curFileInfo}
              onClose={() => setOpen(false)}
            />
          )}
        </Drawer>
      </ConfigProvider>
    </>
  );
};

export default ChatPage;
