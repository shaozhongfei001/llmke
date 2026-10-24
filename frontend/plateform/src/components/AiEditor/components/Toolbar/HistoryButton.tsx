import { useEditorState } from '@udecode/plate-common/react';
import { Button, Tooltip } from 'antd';

const HistoryButton = ({ format, icon }) => {
  const editor = useEditorState();

  const handleClick = () => {
    switch (format) {
      case 'undo':
        editor.undo();
        break;
      case 'redo':
        editor.redo();
        break;
      default:
        return;
    }
  };

  return (
    // <Tooltip title={format}>
    <Button
      size="small"
      style={{ border: 0, background: 'transparent', boxShadow: 'none' }}
      icon={icon}
      onClick={(event) => {
        event.preventDefault();
        if (editor) {
          handleClick();
        }
      }}
    />

  );
};

export default HistoryButton;
