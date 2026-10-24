import { stageTypes } from "../SegmentedWriting/components/Outline/index";
export interface MaterialItem {
  refEntityType: string;
  usage: string;
  refId: string | number;
  refName: string;
  stageType: string;
}

export type MaterialItemWithCustomId = MaterialItem & {
  customId: string;
};
