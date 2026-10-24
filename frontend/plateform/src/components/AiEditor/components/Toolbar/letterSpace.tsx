// import {
//   getPluginType,
//   isBlock,
//   setElements,
//   unsetNodes,
//   type SetNodesOptions,
//   type TNodeMatch,
//   type Value,
// } from '@udecode/plate-common';

// export const KEY_LETTER_SPACING = 'letterSpacing';

// /**
//  * Enables support for text alignment, useful to align your content to left,
//  * right and center it.
//  */
// export const createLetterSpacingPlugin = createPluginFactory({
//   inject: {
//     props: {
//       defaultNodeValue: '2px',
//       nodeKey: KEY_LETTER_SPACING,
//     },
//   },
//   key: KEY_LETTER_SPACING,
//   then: (editor) => ({
//     inject: {
//       props: {
//         validTypes: [getPluginType(editor, ELEMENT_DEFAULT)],
//       },
//     },
//     then: (_, plugin) =>
//       mapInjectPropsToPlugin(editor, plugin, {
//         deserializeHtml: {
//           getNode: (el, node) => {
//             if (el.style.letterSpacing) {
//               node[plugin.key] = el.style.letterSpacing;
//             }
//           },
//         },
//       }),
//   }),
// });

// export const setLetterSpace = <V extends Value>(
//   editor: PlateEditor<V>,
//   { setNodesOptions, value }: { setNodesOptions?: SetNodesOptions<V>; value: string }
// ): void => {
//   const { defaultNodeValue, nodeKey, validTypes } = getPluginInjectProps(
//     editor,
//     KEY_LETTER_SPACING
//   );

//   const match: TNodeMatch = (n) =>
//     isBlock(editor, n) && !!validTypes && validTypes.includes(n.type as string);

//   if (value === defaultNodeValue) {
//     unsetNodes(editor, nodeKey!, {
//       match,
//       ...setNodesOptions,
//     });
//   } else {
//     setElements(
//       editor,
//       { [nodeKey!]: value },
//       {
//         match: match as any,
//         ...setNodesOptions,
//       }
//     );
//   }
// };
