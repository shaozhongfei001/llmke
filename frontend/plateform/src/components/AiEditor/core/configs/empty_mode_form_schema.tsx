import { ProFormColumnsType } from '@ant-design/pro-form';
import { DataItem } from '../../@types/sys';
import { Select } from 'antd';

export const empty_mode_form_schema: ProFormColumnsType<DataItem>[] = [
  {
    title: '标题',
    dataIndex: 'title',
    valueType: 'text',
    formItemProps: {
      rules: [
        {
          required: true,
          message: '请输入标题',
        },
      ],
    },
    fieldProps: (form, cfg) => {
      return {
        placeholder: '请输入标题，最多300字',
      };
    },
  },

  {
    title: '内容描述',
    dataIndex: 'contentAbstract',
    valueType: 'textarea',
    formItemProps: {
      rules: [
        {
          required: true,
          message: '请输入内容描述',
        },
      ],
    },
    fieldProps: (form, cfg) => {
      return {
        placeholder: '请描述文章的简单框架内容，最多500字',
      };
    },
  },
  {
    dataIndex: 'languageStyle',
    valueType: 'select',
    title: '语言风格',
    renderFormItem: () => (
      <Select
        placeholder="请选择"
        options={[
          { label: '正式严谨', value: '正式严谨' },
          { label: '温和礼貌', value: '温和礼貌' },
          { label: '生动活泼', value: '生动活泼' },
          { label: '简洁干练', value: '简洁干练' },
          { label: '热情洋溢', value: '热情洋溢' },
          { label: '口语化', value: '口语化' },
          { label: '辞藻华丽', value: '辞藻华丽' },
        ]}
      />
    ),
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
];
