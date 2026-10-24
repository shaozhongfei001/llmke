import { ProFormColumnsType } from '@ant-design/pro-form';
import dayjs from 'dayjs';
import { DataItem } from '../../@types/sys';

export const notify_mode_form_schema: ProFormColumnsType<DataItem>[] = [
  {
    title: '通知标题',
    dataIndex: 'title',
    valueType: 'text',
    formItemProps: {
      rules: [
        {
          required: true,
          message: '请输入通知标题',
        },
      ],
    },
    fieldProps: (form, cfg) => {
      return {
        placeholder: '请输入通知标题，最多300字',
      };
    },
  },
  {
    title: '通知事项',
    dataIndex: 'contentAbstract',
    valueType: 'textarea',
    formItemProps: {
      rules: [
        {
          required: true,
          message: '请输入通知事项',
        },
      ],
    },
    fieldProps: (form, cfg) => {
      return {
        placeholder: '请输入通知事项，最多300字',
      };
    },
  },
  {
    title: '通知缘由',
    dataIndex: 'reason',
    valueType: 'textarea',
    fieldProps: (form, cfg) => {
      return {
        placeholder: '请输入通知缘由，最多300字',
      };
    },
  },
  {
    title: '执行要求',
    dataIndex: 'requirements',
    valueType: 'textarea',
    fieldProps: (form, cfg) => {
      return {
        placeholder: '请输入执行要求，最多300字',
      };
    },
  },
  {
    title: '结语',
    dataIndex: 'closeWord',
    valueType: 'textarea',
    fieldProps: (form, cfg) => {
      return {
        placeholder: '结语，最多100字',
      };
    },
  },
  {
    title: '主送机关',
    dataIndex: 'target',
    valueType: 'text',
    fieldProps: (form, cfg) => {
      return {
        placeholder: '主送机关，最多100字',
      };
    },
  },
  {
    title: '发文机关',
    dataIndex: 'publisher',
    valueType: 'text',
    fieldProps: (form, cfg) => {
      return {
        placeholder: '发文机关，最多100字',
      };
    },
  },
  {
    title: '字数要求',
    dataIndex: 'lengthLimit',
    valueType: 'digit',
    formItemProps: {},
    fieldProps: (form, cfg) => {
      return {
        placeholder: '期望的字数',
        style: {
          width: '100%',
        },
      };
    },
  },
  {
    title: '选择日期',
    dataIndex: 'publishDate',
    valueType: 'date',
    initialValue: dayjs().format('YYYY-MM-DD'),
    formItemProps: {
      // normalize: (value) => value && dayjs(value).format('YYYY年MM月DD日'),
    },
    fieldProps: (form, cfg) => {
      return {
        placeholder: '选择日期',
        style: {
          width: '100%',
        },
        getValueProps: (value) => ({ value: value && dayjs(value).format('YYYY年MM月DD日') }),
        format: (value) => value && dayjs(value).format('YYYY年MM月DD日'),
      };
    },
  },
];
