import { Button, ConfigProvider, Modal } from "antd";
import xls from "../../assets/icon/icon-xls.svg";
import csv from "../../assets/icon/icon-csv.svg";
import txt from "../../assets/icon/icon-txt.svg";
import doc from "../../assets/icon/icon-doc.svg";
import pdf from "../../assets/icon/icon-pdf.svg";
import ppt from "../../assets/icon/icon-ppt.svg";
import img from "../../assets/icon/icon-png.svg";
import FileView from "./FileView";

export const FILEIMG: any = {
  docx: doc,
  doc: doc,
  pdf: pdf,
  xls: xls,
  xlsx: xls,
  ppt: ppt,
  pptx: ppt,
  pub: ppt,
  txt: txt,
  csv: csv,
  png: img
};
const FileViewModal = ({
  showPreviewModal,
  setShowPreviewModal,
  curFileInfo
}: any) => {
  const modalStyles = {
    header: { margin: 0 },
    body: {},
    mask: {},
    footer: {},
    content: { padding: 0 }
  };
  return (
    <ConfigProvider
      modal={{
        styles: modalStyles
      }}
    >
      <Modal
        destroyOnClose={true}
        footer={
          <div
            className="px-[20px] py-[16px] text-right"
            style={{ borderTop: "1px solid #F0F0F0" }}
          >
            <Button
              type="text"
              onClick={() => setShowPreviewModal(false)}
              style={{ border: "1px solid #EBEBEB" }}
              className="text-text-color2"
            >
              关闭
            </Button>
          </div>
        }
        title={
          <div className="flex " style={{ borderBottom: "1px solid #F0F0F0" }}>
            <img
              src={FILEIMG[curFileInfo?.file_type] || FILEIMG.doc}
              alt="ellipse"
              className="mt-[20px] ml-[20px] w-[20px] h-[20px]"
            />
            <div className="mt-[20px] mb-[16px] ml-[12px] text-[16px]">
              {`${curFileInfo?.title}.${curFileInfo?.file_type}`}
            </div>
          </div>
        }
        open={showPreviewModal}
        onCancel={() => setShowPreviewModal(false)}
        width={1118}
        height={742}
        className="viewModal"
      >
        <div className="px-[20px] pt-[20px]">
          <FileView
            fileName={`${curFileInfo?.title}.${curFileInfo?.file_type}`}
            fileUrl={curFileInfo?.metadata?.source}
          />
        </div>
      </Modal>
    </ConfigProvider>
  );
};

export default FileViewModal;
