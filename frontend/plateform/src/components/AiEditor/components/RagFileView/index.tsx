/* eslint-disable no-case-declarations */

import FileView3 from "@root/src/components/FileView3";
import { ConfigProvider, Modal } from "antd";
import { useEffect, useState } from "react";

// display_file_type: "doc",
//           file_source: data.convertedFilePath,
//           file_name: data.name,

export const RagFileView = ({ curFileInfo }: any) => {
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  useEffect(() => {
    if (!curFileInfo) return;
    setShowPreviewModal(true);
  }, [curFileInfo]);

  const handleE = (type: string) => {
    switch (type) {
      case "close":
        setShowPreviewModal(false);
        break;
    }
  };

  return (
    <ConfigProvider
      modal={{
        styles: {
          header: {
            padding: "20px 24px",
            borderBottom: "1px solid #F0F0F0",
            margin: 0
          },
          body: { padding: 0 },
          mask: {},
          footer: { padding: 0, margin: 0 },
          content: {
            padding: 0
          }
        }
      }}
    >
      <Modal
        destroyOnClose={true}
        footer={null}
        open={showPreviewModal}
        onCancel={() => setShowPreviewModal(false)}
        width={900}
        height={742}
        closable={false}
      >
        <div className="h-[600px] overflow-y-auto">
          <FileView3 curFileInfo={curFileInfo} handleEvent={handleE} />
        </div>
      </Modal>
    </ConfigProvider>
  );
};
