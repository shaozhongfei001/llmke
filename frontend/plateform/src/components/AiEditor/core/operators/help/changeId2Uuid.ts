import { v4 as uuidv4 } from "uuid";
const retrieveTag = "retrieve-tag";

const parseRetrieveTag = (
  inputString: string,
  isReplaceId: boolean = false
) => {
  const regex = isReplaceId
    ? /(.*?)<retrieve-tag\s+([^>]*)>(.*?)<\/retrieve-tag>(.*)/s
    : /(.*?)\[retrieve-tag\s+([^\]]+)\]([^[]+)\[\/retrieve-tag\](.*)/s;
  const match = inputString.match(regex);

  if (match) {
    const beforeTag = match[1];
    const attributesString = match[2].trim();
    const content = match[3];
    const afterTag = match[4];
    const attributes: { [key: string]: string } = {};
    const attributePairs = attributesString.split(/\s+/);

    for (const pair of attributePairs) {
      const [key, value] = pair.split("=");
      if (key && value) {
        attributes[key.trim()] = value.trim().replace(/^['"](.*?)['"]$/, "$1");
      }
    }
    return {
      beforeTag,
      attributes,
      content,
      afterTag
    };
  } else {
    console.log(
      new Error("Invalid input string format"),
      inputString,
      isReplaceId
    );
    return {};
  }
};

// 分段写作将每次分段返回的溯源id修改为不重复的uuid
export const changeId2Uuid = (curRes: any, matchLen: number) => {
  const { match, reply } = curRes;
  const id = uuidv4();
  const { beforeTag, attributes, content, afterTag } = parseRetrieveTag(
    reply.content,
    true
  );
  curRes.match = Object.assign({}, match, { id });
  if (attributes && content) {
    const attrStr = (Object.keys(attributes) || [])
      .map((key) => {
        return key === "id" ? `id=${id}` : `${key}=${attributes[key]}`;
      })
      .join(" ");
    const _content = `${beforeTag}<${retrieveTag} ${attrStr}>${content}</${retrieveTag}>${afterTag}`;
    curRes.reply = Object.assign({}, reply, {
      content: _content
    });
  }
};
