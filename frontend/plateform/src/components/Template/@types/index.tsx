export interface IusePromptDsigner {
  defaultValue?: string;
  themeStyles?: any;
  layoutProps?: any;
  token: string;
  name: string;
  sceneClass: string[];
  sceneKey: string;
  sceneClassTag: string;
  isSegment: boolean;
  isVersion?: boolean;
  sensitiveWords?: ICheckedData[];
}

export interface Example {
  getOutput: (InoutValue: any) => {
    promptTemplate: string;
    formSchema: IFormSchema[];
  };
}

interface Location {
  x: number;
  y: number;
}
interface IFormSchema {
  id: string;
  label: string;
  value: string;
  isOption: boolean;
  locations: Location[];
}
export interface ICheckedData {
  id: string;
  name: string;
}
