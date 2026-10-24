import { getMark, indent, outdent } from '@udecode/plate';
import { useEditorState } from '@udecode/plate-common/react';
import { Button, Tooltip } from 'antd';

const IndentButton = ({ format, icon }) => {
  const editor = useEditorState();
  const { selection } = editor;
  const isMarkActive = () => {
    if (!editor) return false;
    const marks = getMark(editor, format);
    return !!marks?.[format]; // Check if the mark is applied to the current selection
  };

  return (
    // <Tooltip title={format}>
      <Button
        size="small"
        style={{ border: 0, background: 'transparent', boxShadow: 'none' }}
        type={isMarkActive() ? 'primary' : 'default'} // Changes the button style based on whether the mark is active
        icon={icon}
        onClick={(event) => {
          event.preventDefault();
          if (editor) {
            if (format === 'indent') {
              indent(editor, { offset: 1 });
            }

            if (format === 'outdent') {
              outdent(editor, { offset: -1 });
            }
          }
        }}
      />

  );
};

export default IndentButton;
