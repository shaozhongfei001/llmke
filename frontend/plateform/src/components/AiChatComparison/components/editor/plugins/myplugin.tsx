import { PluginConfig } from "@udecode/plate";
import { createPlatePlugin } from "@udecode/plate/react";
import { PlateElement, PlateElementProps } from '@udecode/plate-common/react';
import { TLinkElement } from '@udecode/plate-link';

type MyPluginConfig = PluginConfig<
  string,  // 使用 string 而不是具体的字符串字面量
  { customOption: boolean },
  { getData: () => string },
  { customTransform: () => void }
>
export function LinkElement({ attributes, children, element, editor }: PlateElementProps<TLinkElement>) {
  const { url } = element;
  console.log('进组建了')
  return (
    <a {...attributes} className=" text-sky-800" href={url}>
      {children}
    </a>
  );
}

export const MyPlugin = createPlatePlugin({
  key: "myPlugin",  // 这里的 key 被正确识别为 string
  // options: {
  //   customOption: true
  // },
  node: {
    isElement: true,
    type: 'p',
  },
  // api: {
  //   getData: () => {
  //     console.log('good');
  //     return 'kdkdkdk';
  //   }
  // },
  // node: {
  //   component: LinkElement,
  //   isElement: true,
  //   type: 'a'
  // },
  // transforms: {
  //   // 遍历 Slate 文档，找到包含 <a> 标签的文本节点并转换它们
  //   customTransform: (editor) => {
  //     const { children } = editor;

  //     const transformedChildren = children.map(node => {
  //       if (typeof node.text === 'string') {
  //         const regex = /<a\s+([^>]*)id="([^"]*)"([^>]*)>(.*?)<\/a>/g;
  //         const newChildren: any[] = [];
  //         let lastIndex = 0;
  //         let match;

  //         while ((match = regex.exec(node.text)) !== null) {
  //           if (match.index > lastIndex) {
  //             newChildren.push({ text: node.text.slice(lastIndex, match.index) });
  //           }
  //           newChildren.push({
  //             type: 'a',
  //             id: match[2],
  //             attributes: match[1] + match[3],
  //             children: [{ text: match[4] }]
  //           });
  //           lastIndex = regex.lastIndex;
  //         }

  //         if (lastIndex < node.text.length) {
  //           newChildren.push({ text: node.text.slice(lastIndex) });
  //         }

  //         return newChildren.length > 0 ? newChildren : node;
  //       }
  //       return node;
  //     });

  //     editor.children = transformedChildren;
  //     return editor;
  //   },
  // },
  // render: {
  //   // 自定义渲染逻辑
  //   node: (props) => {
  //     const { attributes, children, element } = props;
  //     console.log(props, 'zheli')
  //     if (element.type === 'a') {
  //       return <LinkElement {...props} />;
  //     }
  //     return (
  //       <div {...attributes}>
  //         <p>自定义插件节点：{element.type}</p>
  //         {children}
  //       </div>
  //     );
  //   }
  // },
  // plugin implementation
});
// export const MyPlugin = MPlugin.withComponent(LinkElement)