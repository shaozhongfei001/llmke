import { PieChartOutlined } from '@ant-design/icons';
import { ModueEnum, ModuleStatus } from '../../@types/sys';

export const modules_set = [
  {
    name: '写作',
    value: ModueEnum.Writing,
    icon: <PieChartOutlined />,
    formData: {},
    status: ModuleStatus.Waiting,
    uiSchema: [],
  },
  // {
  //   name: '润色',
  //   value: ModueEnum.Polish,
  //   icon:<PieChartOutlined />,
  //   formData: {},
  // },
  {
    name: '审核',
    value: ModueEnum.Review,
    icon: <PieChartOutlined />,
    formData: {},
  },
  {
    name: '素材',
    value: ModueEnum.Material,
    icon: <PieChartOutlined />,
    formData: {},
  },
];
