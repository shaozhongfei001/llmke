import { useEditorState } from '@udecode/plate-common/react';
import { Button } from 'antd';
// import Html2canvas from 'html2canvas';
// import jsPDF from 'jspdf';
const DownLoadButton = () => {
  const editor = useEditorState();
  const toDownload = () => {
    const htmlContent: any = document.querySelector('div[role="textbox"]');
    if (!htmlContent) return;
    // Html2canvas(htmlContent).then((canvas) => {
    //   const imgData = canvas.toDataURL('image/png');
    //   const pdf = new jsPDF({
    //     orientation: 'landscape',
    //   });
    //   const imgProps: any = pdf.getImageProperties(imgData);
    //   const pdfWidth = pdf.internal.pageSize.getWidth();
    //   const pdfHeight = (imgProps.height * pdfWidth) / imgProps.width;
    //   pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
    //   pdf.save('download.pdf');
    // });

    // const pdf: any = new jsPDF();
    // pdf.fromHTML(htmlContent, 15, 15, {}, () => {
    //   // 保存 PDF 文件
    //   pdf.save('output.pdf');
    // });
    // const tt = serializeMd(editor);
    // console.log('====', tt);
    console.log('editor-------->', editor);
  };
  return (
    <Button size="small" type="default" onClick={toDownload}>
      下载
    </Button>
  );
};

export default DownLoadButton;
