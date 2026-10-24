interface IToolbarItem {
  type: 'button' | 'select' | 'pick' | 'customized';
  name: string;
  options?: any[];
  tip?: string;
  label?: string;
  icon?: any;
}
