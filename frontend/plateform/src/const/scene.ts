export enum sceneTypes {
  FULL_WRITING = "fullWriting",
  SEGMENTED_WRITING = "segmentedWriting"
}

export const sceneList = [
  {
    key: sceneTypes.FULL_WRITING,
    label: "全文生成模版",
    dsc: "一键生成整篇文章，快速完成从起稿到定稿的全过程。"
  },
  {
    key: sceneTypes.SEGMENTED_WRITING,
    label: "分段生成模版",
    dsc: "逐段生成内容，灵活编辑，轻松掌控文章细节。"
  }
];
