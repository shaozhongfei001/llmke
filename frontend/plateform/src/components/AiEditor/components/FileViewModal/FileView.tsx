import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import chardet from "chardet";
import { Select, Table, message, Input, Flex } from "antd";
import { v4 as uuidv4 } from "uuid";
import Papa from "papaparse";
import { pdfjs } from "react-pdf";
import Loading from "./Loading";

const { Search } = Input;

interface Iprops {
  fileUrl: string;
  fileName: any;
}

function FileView(props: Iprops) {
  const { fileUrl, fileName } = props;
  const pdfContainer = useRef<HTMLDivElement | null>(null);
  const [fileContent, setFileContent] = useState<any>("");
  const [loading, setLoading] = useState(false);
  const [isError, setIsError] = useState<boolean>(false);

  const fileExtension = useMemo(
    () => (fileName ? fileName.split(".").pop().toLowerCase() : ""),
    [fileName]
  );

  const parseCsvContent = (res: string, encodeing: string) => {
    Papa.parse(res, {
      header: true,
      encoding: encodeing,
      complete: function (result: { data: any }) {
        //  解析csv文件
        setFileContent(result.data);
        setLoading(false);
      },
      error: function (error: { message: any }) {
        message.error("解析CSV失败:", error.message);
        setLoading(false);
      }
    });
  };

  async function fetchFileContent() {
    try {
      setLoading(true);
      const response = await fetch(fileUrl, {
        // headers: {
        //   Authorization: token(),
        // },
      });
      if (response.status !== 200) {
        setFileContent("暂无文件信息");
        setIsError(true);
        setLoading(false);
        return;
      } else {
        setIsError(false);
      }

      // if (["doc", "docx"].includes(fileExtension)) {
      //   const arrayBuffer = await response.arrayBuffer();
      //   // console.log(arrayBuffer.toString())
      //   // const text = await mammoth.extractRawText({ arrayBuffer });
      //   // console.log(text)
      //   // setFileContent(text.value);
      //   // setLoading(false);
      //   console.log('ArrayBuffer Size:', arrayBuffer.byteLength);  // 调试 ArrayBuffer 大小

      //   try {
      //     const text = await mammoth.extractRawText({ arrayBuffer });
      //     console.log('Extracted Text:', text.value);  // 调试提取的文本
      //     setFileContent(text.value);
      //   } catch (error) {
      //     console.error('Mammoth Error:', error);  // 错误日志
      //   }
      //   setLoading(false);
      //   // csv
      // } else if (fileExtension === "csv") {
      //   const encodeing = "UTF-8";
      //   response.arrayBuffer().then((res) => {
      //     const type = "csv/*";
      //     const blob = new Blob([res], { type: type });
      //     const reader = new FileReader();
      //     reader.readAsText(blob, encodeing);
      //     reader.onload = function (f) {
      //       parseCsvContent(this.result as string, encodeing);
      //     };
      //   });

      //   // txt
      // } else

      if (fileExtension === "pdf") {
        const arrayBuffer = await response.arrayBuffer();
        const data = new Uint8Array(arrayBuffer);
        const loadingTask = pdfjs.getDocument({ data });
        const pdf = await loadingTask.promise;
        const numPages = pdf.numPages;
        const pdfText: any[] = [];
        for (let pageNum = 1; pageNum <= numPages; pageNum++) {
          const page = await pdf.getPage(pageNum);
          const textContent = await page.getTextContent();
          const pageText = textContent.items
            .map((item: any) => item.str)
            .join("");
          pdfText.push(pageText);
        }
        setFileContent(pdfText.join("\n"));
        setLoading(false);
      } else {
        const arrayBuffer = await response.arrayBuffer();
        const detectedEncoding = chardet.detect(new Uint8Array(arrayBuffer));
        const text = detectedEncoding
          ? new TextDecoder(detectedEncoding).decode(arrayBuffer)
          : "";
        setFileContent(text);
        setLoading(false);
      }
    } catch (error) {
      setIsError(true);
      setLoading(false);
      setFileContent("暂无文件信息");
    }
  }

  useEffect(() => {
    if (fileUrl) {
      if (fileExtension == "pdf") {
        displayPdfInIframe();
        // console.log('fileurl', fileUrl)
      } else {
        fetchFileContent();
      }
    }
  }, [fileUrl, pdfContainer.current]);

  const displayPdfInIframe = async () => {
    setLoading(true);
    try {
      const response = await fetch(fileUrl);
      if (!response.ok) throw new Error("Failed to fetch the PDF.");

      const originalBlob = await response.blob();
      const correctedBlob = new Blob([originalBlob], {
        type: "application/pdf"
      }); // Ensure PDF MIME type
      if (pdfContainer.current) {
        const blobUrl = URL.createObjectURL(correctedBlob);
        const iframe = document.createElement("iframe");
        iframe.src = blobUrl;
        iframe.style.width = "100%";
        iframe.style.height = "606px";
        pdfContainer.current.innerHTML = "";
        pdfContainer.current.appendChild(iframe);

        return () => URL.revokeObjectURL(blobUrl);
      }
    } catch (error) {
      console.error("Error displaying PDF:", error);
    } finally {
      setLoading(false);
    }
  };

  // 预览CSV文件的列定义
  const columns = useMemo(() => {
    if (
      fileContent &&
      typeof fileContent !== "string" &&
      fileExtension === "csv"
    ) {
      const colNum = (Object.keys(fileContent[0]) || []).length;
      return fileContent.length > 0
        ? Object.keys(fileContent[0]).map((header) => ({
            title: header,
            dataIndex: header,
            textWrap: "word-break",
            width: `${(1 / colNum) * 100}%`
          }))
        : [];
    } else {
      return [];
    }
  }, [fileContent, fileExtension]);

  // csv表格检索
  const [searchCol, serSearchCol] = useState<string>("");
  const handleColChange = (value: string) => serSearchCol(value);
  const [csvData, setCsvData] = useState<any>();
  const tableData = useMemo(() => {
    return csvData || fileContent;
  }, [fileContent, csvData]);
  const handleSearch = (searchKeyWord: string) => {
    const newData: any[] = [];
    fileContent.forEach((row: any) => {
      if (row[searchCol]) {
        row[searchCol].includes(searchKeyWord) ? newData.push(row) : "";
      }
    });
    setCsvData(newData);
  };
  const searchTitle = useCallback(
    () => (
      <div className="flex-grow flex justify-end gap-x-3">
        <div className="flex items-center">
          <div>搜索列：</div>
          <Select
            className="w-[200px]"
            value={searchCol}
            onChange={handleColChange}
            options={
              columns
                ? columns.map((i) => ({
                    value: i.title,
                    label: i.title
                  }))
                : []
            }
          />
        </div>
        <Search
          placeholder={"请输入搜索内容"}
          className="w-[320px]"
          enterButton="搜索"
          disabled={!searchCol}
          onSearch={handleSearch}
        />
      </div>
    ),
    [columns, searchCol]
  );

  return (
    <div style={{ height: "616px", overflowY: "auto", overflowX: "hidden" }}>
      {loading && <Loading />}
      {!loading && !isError && (
        <>
          {fileExtension === "csv" && (
            <>
              {typeof fileContent === "string" ? (
                <div>{fileContent}</div>
              ) : (
                <Table
                  title={searchTitle}
                  dataSource={tableData}
                  columns={columns}
                  loading={loading}
                  rowKey={() => uuidv4()}
                  className="h-full"
                  tableLayout="auto"
                  bordered={false}
                  size="small"
                  pagination={{ position: ["bottomCenter"], size: "small" }}
                />
              )}
            </>
          )}
          {fileExtension == "pdf" && (
            <div
              className="w-full h-full"
              ref={pdfContainer}
              id="pdfContainer"
            ></div>
          )}
          {fileExtension !== "csv" && fileExtension !== "pdf" && (
            <div>
              {/* <h2>文件预览: {fileName}</h2> */}
              <div>
                <pre style={{ whiteSpace: "pre-wrap" }}>{fileContent}</pre>{" "}
              </div>
            </div>
          )}
        </>
      )}
      {!loading && isError && (
        <div>
          {/* <h2>文件预览: {fileName}</h2> */}
          <div>
            <pre style={{ whiteSpace: "pre-wrap" }}>{"文件解析出错"}</pre>{" "}
          </div>
        </div>
      )}
    </div>
  );
}
export default FileView;
