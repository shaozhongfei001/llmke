import {
  mainEditorDefaultComponents,
  mainEditorDefaultPlugins,
} from "@root/src/components/AiEditor/components/editor/plugins/mainEditorSet";
import {
  createPlateEditor,
  Plate,
  PlateContent,
} from "@udecode/plate-common/react";
import { MentionPlugin } from "@udecode/plate-mention";
import { useMemo } from "react";
const injectStyle = (plugin: any, styles: any) => {
  if (plugin.key === MentionPlugin.key) {
    return {
      ...plugin,
      // 这里存的样式分2个部分，标签的样式，自定义的class的样式
      inject: {
        ...styles,
      },
    };
  } else {
    return plugin;
  }
};
const TempPreview = (props: { htmlTemp: string; cssTemp: any }) => {
  const { htmlTemp, cssTemp } = props;

  const mainWritingSet = useMemo(() => {
    if (!htmlTemp || !cssTemp) {
      return createPlateEditor({
        id: "tempPreview",
        value: [{ type: "p", children: [{ text: "" }] }],
      });
    }
    const adjustedPlugins = mainEditorDefaultPlugins.map((plugin) => {
      return injectStyle(plugin, cssTemp);
    });
    return createPlateEditor({
      plugins: adjustedPlugins,
      override: { components: mainEditorDefaultComponents },
      id: "tempPreview",
      value: htmlTemp,
    });
  }, [cssTemp, htmlTemp]);

  return (
    <Plate editor={mainWritingSet}>
      <div className="bg-white w-[729px] px-[5rem] pt-[4.3rem] pb-[3.5rem]">
        <PlateContent readOnly={true} />
      </div>
    </Plate>
  );
};

export default TempPreview;
