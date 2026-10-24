export interface IReference {
  id: string;
  title: string;
  file_type: string;
  file_source: string;
  metadata: any;
  contents: any[];
  pic_url_list?: any[];
  pdfPages: number;
  file_name: string;
}
