// ... existing imports ...

import { useCallback, useEffect } from "react";
import { useStateStore } from "../../core/states/useStateStore";
import FullWriting from "./FullWriting/newIndex";
import SegmentedWriting from "./SegmentedWriting/newIndex";
import { api_getArticleById } from "../../core/services/servers";
import { useDataTransformer } from "../../core/useDataTransformer";

const WritingConfig = () => {
  const {
    writingSettingOpen,
    projectData,
    setWritingSettingOpen,
    serverInfo,
    setProjectData
  } = useStateStore();
  const { toProjectData } = useDataTransformer();

  // 关闭时重新获取文章数据刷新页面内容
  const handleClose = useCallback(async () => {
    if (projectData.id) {
      const articleInfo = await api_getArticleById({
        data: {
          articleId: projectData.id,
          needSectionContent: true
        },
        config: serverInfo
      });
      const newPd = toProjectData(articleInfo);
      setProjectData((p) => {
        return {
          ...p,
          ...newPd
        };
      });
    }
    setWritingSettingOpen(false);
  }, [projectData.id]);

  return (
    <>
      {writingSettingOpen &&
        (!projectData.generateType ? (
          <FullWriting
            open={writingSettingOpen}
            articelInfo={projectData?.articelInfo}
            onClose={handleClose}
          />
        ) : (
          <SegmentedWriting open={writingSettingOpen} onClose={handleClose} />
        ))}
    </>
  );
};

export default WritingConfig;
