export const contentARegex = /\[(\d+)\]/g;
// 正则，适配[retrive-tag id="1525846256543391688" image_urls=""][2][/retrive-tag]，并解析出来id image_urls和数字
export const modelRegex =
  /\[retrive-tag id="(\d+)" image_urls="([^"]*)" fromType="([^"]*)"\]\[(\d+)\]\[\/retrive-tag\]/g;

export const startARegex = /\[retrive-tag id="(\d+)" image_urls="([^"]*)"\]/; //

export const replaceRetriveReg =
  /\[retrive-tag (.*?)\](.*?)\[(.*?)\]\[\/retrive-tag\]/g;

export const replacedRetrive = "<retrive-tag $1>$2[$3]</retrive-tag>";

export const RETRIVE_TAG = "[retrive-tag";
