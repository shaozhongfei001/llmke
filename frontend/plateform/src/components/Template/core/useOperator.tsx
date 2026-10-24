import { isText } from '@udecode/plate';
import { Node } from 'slate';
import { regex } from './constants';
import { generateRow } from '../components/TableList';

const useOperator = ({
  restList,
  setRestList,
  setIsModalOpen,
  tableList,
  setTableList,
  editor,
}) => {
  const serialize = (nodes) => {
    return nodes.map((n) => Node.string(n)).join('\n');
  };

  const getStr = (str: string) => {
    const match = str.match(regex);

    if (match) {
      const extractedText = match[1];
      return extractedText;
    } else {
      return '';
    }
  };

  const getUnusedTableData = (data: any[]) => {
    const res: any = [];
    const dataSourceArr = tableList.map((item) => item.dataIndex);
    data.forEach((item) => {
      if (!dataSourceArr.includes(item)) {
        res.push(item);
      }
    });
    return res;
  };

  const handlerEvent = (type: string, data?: any) => {
    switch (type) {
      case 'onContextMenu':
        data.preventDefault();
        break;
      case 'addTableList':
        setTableList([
          ...tableList,
          ...restList.map((item) => {
            return generateRow(item);
          }),
        ]);
        setIsModalOpen(false);
        break;
      case 'onBlur':
        if (!editor) return;
        console.log('======blur');
        const set: any = new Set();
        for (const [node, path] of Node.texts(editor)) {
          if (isText(node)) {
            const text = Node.string(node);
            const match = regex.exec(text);
            if (match !== null) {
              const str = getStr(node.text);
              str && set.add(str);
            }
          }
        }
        const arr = [...set];
        if (!arr.length) return;

        const res = getUnusedTableData(arr);
        if (!res.length) return;
        setRestList(res);
        setIsModalOpen(true);
        break;
    }
  };
  return { handlerEvent, serialize };
};
export default useOperator;
