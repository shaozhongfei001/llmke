import { ProFormColumnsType } from '@ant-design/pro-form';
import dayjs from 'dayjs';
import { DataItem } from '../../@types/props';

export const request_mode_form_schema: ProFormColumnsType<DataItem>[] = [
  {
    title: '发文机关',
    dataIndex: 'publisher',
    valueType: 'text',
    formItemProps: {
      rules: [
        { required: true, message: '请填写发文机关' },
        { max: 100, message: '最大字数限制100' },
      ],
    },
    fieldProps: (form, cfg) => {
      return {
        placeholder: '发文机关，最多100字',
      };
    },
  },
  {
    title: '发文字号',
    dataIndex: 'documentNumber',
    valueType: 'text',
    formItemProps: {
      rules: [
        { required: true, message: '请填写发文字号' },
        { max: 50, message: '最大字数限制50' },
      ],
    },
    fieldProps: (form, cfg) => {
      return {
        placeholder: '发文字号，最多100字',
      };
    },
  },
  {
    title: '通知事项',
    dataIndex: 'contentAbstract',
    valueType: 'textarea',
    formItemProps: {
      rules: [
        { required: true, message: '通知事项' },
        { max: 300, message: '最大字数限制300' },
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
    formItemProps: {
      rules: [{ max: 300, message: '最大字数限制300' }],
    },
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
    formItemProps: {
      rules: [{ max: 300, message: '最大字数限制300' }],
    },
    fieldProps: (form, cfg) => {
      return {
        placeholder: '请输入通知缘由，最多300字',
      };
    },
  },
  {
    title: '结语',
    dataIndex: 'closeWord',
    valueType: 'textarea',
    formItemProps: {
      rules: [{ max: 100, message: '最大字数限制100' }],
    },
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
    formItemProps: {
      rules: [
        { required: true, message: '请填写主送机关' },
        { max: 300, message: '最大字数限制300' },
      ],
    },
    fieldProps: (form, cfg) => {
      return {
        placeholder: '主送机关，最多100字',
      };
    },
  },
  {
    title: '选择日期',
    dataIndex: 'publishDate',
    valueType: 'date',
    formItemProps: {
      normalize: (value) => value && dayjs(value).format('YYYY年MM月DD日'),
      rules: [{ required: true, message: '请选择发文时间' }],
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
  {
    title: '联系人',
    dataIndex: 'publisher',
    valueType: 'text',
    formItemProps: {
      rules: [
        { required: true, message: '请填写联系人' },
        { max: 100, message: '最大字数限制100' },
      ],
    },
    fieldProps: (form, cfg) => {
      return {
        placeholder: '请输入联系人',
      };
    },
  },
  {
    title: '联系方式',
    dataIndex: 'publisher',
    valueType: 'text',
    formItemProps: {
      rules: [
        { required: true, message: '请填写联系方式' },
        { max: 13, message: '最大字数限制100' },
      ],
    },
    fieldProps: (form, cfg) => {
      return {
        placeholder: '请输入联系方式',
      };
    },
  },
];
