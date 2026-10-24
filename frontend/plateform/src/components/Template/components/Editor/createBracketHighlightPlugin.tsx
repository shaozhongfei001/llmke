import { Transforms, Text, Node } from 'slate';
export const BRACKETHIGHLIGHTKEY = 'bracketHighlight';
import { defaultColor, primaryColor, regex } from '../../core/constants';
import { createPlatePlugin } from '@udecode/plate/react';

export const createBracketHighlightPlugin = createPlatePlugin({
  key: BRACKETHIGHLIGHTKEY,
  handlers: {
    onChange: ({ editor }) => {
      try {
        const _Transforms: any = Transforms;

        for (const [node, path] of Node.texts(editor)) {
          const text = Node.string(node);
          const match: any = regex.exec(text);
          if (match) {
            const [wrapText, innerText] = match;
            const start = match.index;
            const end = start + wrapText.length;
            _Transforms.setNodes(
              editor,
              { color: primaryColor },
              {
                at: {
                  anchor: { path, offset: start },
                  focus: { path, offset: end },
                },
                match: (node, path) => {
                  return Text.isText(node);
                },
                split: true,
              }
            );
            if (start !== 0) {
              _Transforms.setNodes(
                editor,
                { color: defaultColor },
                {
                  at: {
                    anchor: { path, offset: 0 },
                    focus: { path, offset: start },
                  },
                  match: (node, path) => {
                    return Text.isText(node);
                  },
                  split: true,
                }
              );
            }
            if (end !== text.length) {
              _Transforms.setNodes(
                editor,
                { color: defaultColor },
                {
                  at: {
                    anchor: { path, offset: end },
                    focus: { path, offset: text.length },
                  },
                  match: (node, path) => {
                    return Text.isText(node);
                  },
                  split: true,
                }
              );
            }
          } else {
            const _node: any = node;
            const textNodes = [...Node.texts(editor)];

            if (textNodes.length === 1 && (!_node.color || _node.color === defaultColor)) {
              return;
            }
            _Transforms.setNodes(
              editor,
              { color: defaultColor },
              {
                at: {
                  anchor: { path, offset: 0 },
                  focus: { path, offset: text.length },
                },
                match: (node, path) => {
                  return Text.isText(node);
                },
                split: true,
              }
            );
          }
        }
      } catch (error) {
        console.log('onChange error', error);
      }
    },
  },
});
