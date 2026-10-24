import { Flex } from "antd";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";

const MarkdownRender = (props: any) => {
  console.log("props.children", props.children);
  // const reg = /\<td\>(.*?)\<\/td\>/g;
  const reg = /<td>(.*?)<\/td>/g;

  const matches = props.children.match(reg);

  // 如果找到了匹配项，提取出实际的内容
  const results = matches
    ? matches.map((match: any) => {
        // 再次使用正则表达式来提取标签内的文本
        const contentPattern = /<td>(.*?)<\/td>/;
        const result = contentPattern.exec(match);
        if (result && result.length > 1) {
          return result[1];
        } else {
          return "";
        }
      })
    : [];

  const abnormalStrs = results.filter(
    (i: any) => i.indexOf("<") > -1 || i.indexOf(">") > -1
  );

  let formatStr = props.children;
  abnormalStrs.forEach((item: any) => {
    const aaa = item.replaceAll("<", "</"); // distroy the dectecting of html tags, e.g. <td>P01<IND00116109<P02; and IND0011674>P02;</td> will lead to error

    formatStr = formatStr.replace(item, aaa);
  });

  return (
    <Flex
      className="max-w-[800px] px-3 overflow-y-auto whitespace-break-spaces break-words "
      style={{
        backgroundColor: "#F9F9F9",
        fontFamily: "PingFang SC",
        letterSpacing: "0.06em",
        fontSize: "14px",
        height: "100%",
        maxHeight: props.autoHeight ? "none" : "600px",
        minWidth: props.autoHeight ? "none" : "600px"
      }}
      vertical
    >
      <ReactMarkdown children={formatStr} rehypePlugins={[rehypeRaw]} />
    </Flex>
  );
};

export default MarkdownRender;
