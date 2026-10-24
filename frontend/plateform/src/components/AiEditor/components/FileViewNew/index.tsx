import { Pagination } from "antd";
import React, { useState, useEffect, useRef } from "react";
import { useFileViewer, registerPDFWorker } from "@mxmweb/fv";
registerPDFWorker("/worker/pdf.worker.min.js");
import "@mxmweb/fv/style.css";
import { uid } from "uid";
import { dealMinioUrl } from "@root/src/core/helps";

interface IFile {
  curFile: any;
  curChunk: any;
  total: number;
  origin_paper_size: {
    width: number;
    height: number;
  };
}

const IMAGEBGCOLOR = "rgba(225,238,223,.5)";
const TEXTBGCOLOR = "rgba(96,139,255,.2)";

const FileViewNew = ({
  curFile,
  origin_paper_size,
  total,
  curChunk
}: IFile) => {
  const pdfBoxRef = useRef(null);
  const [curPositions, setCurPositions]: any = useState([]);
  const [renderWidth, setRenderWidth] = useState(660);
  const [current, setCurrent] = useState(1);
  const [pagePosition, setPagePosition] = useState<any>({
    left: 0,
    right: 0
  });

  const handleFileViewer = (type: string) => {
    switch (type) {
      case "pdfSuccess":
        setTimeout(() => {
          mark();
        }, 100);
        break;
    }
  };

  const { Element, pdfRef, mdRef } = useFileViewer({
    fileUrl: dealMinioUrl(curFile.url),
    form: curFile.fileExtension,
    annotation: {
      method: curFile.fileExtension === "pdf" ? "position" : "",
      data: curPositions,
      origin_paper_size
    },
    bgColor: "#fff",
    render_width: renderWidth,
    hide_toolbar: true,
    actionOnEmmit: handleFileViewer
  });

  const changePage = (page: number) => {
    if (pdfRef?.current?.pageChange) {
      setCurrent(page);
      pdfRef.current.pageChange(page);
    }
  };

  const pagiChange = (page: number) => {
    changePage(page);
    if (!curChunk) {
      setCurPositions([]);
      return;
    }
    const pageIndexs: any = [];
    (curChunk.pageNumbers || []).forEach((c: number, i: number) => {
      if (c === page) {
        pageIndexs.push(i);
      }
    });
    if (!pageIndexs.length) {
      setCurPositions([]);
      return;
    }

    const ps: any = pageIndexs.map((pageIndex: number) => {
      const item = curChunk.positions[pageIndex];

      return {
        id: uid(),
        page,
        anotation_color:
          curChunk?.type === "image" ? IMAGEBGCOLOR : TEXTBGCOLOR,
        position: item
      };
    });

    setCurPositions(ps);
  };

  const mark = () => {
    const { metadata, id } = curChunk;
    if (id && metadata) {
      console.log(pdfRef.current);
      setTimeout(() => {
        const { offset, page_number, position, type } = metadata;
        if (curFile.fileExtension === "md") {
          if (mdRef?.current?.heightLight) {
            mdRef.current.heightLight({
              positions: offset && offset.length ? offset : []
            });
          }
        } else {
          if (!page_number || !page_number?.length) {
            console.log("%c缺少文件页数", "color: red");
            return;
          }
          const pageNumber = page_number[0];
          changePage(pageNumber);
          const pageIndexs: any = [];
          page_number.forEach((c: number, i: number) => {
            if (c === pageNumber) {
              pageIndexs.push(i);
            }
          });
          let _position = position;
          if (position && position.length) {
            if (
              Object.prototype.toString.call(position) === "[object String]"
            ) {
              _position = JSON.parse(_position);
            }
            const ps: any = pageIndexs.map((pageIndex: number) => {
              const item = _position[pageIndex];
              return {
                id: uid(),
                page: pageNumber,
                anotation_color: type === "image" ? IMAGEBGCOLOR : TEXTBGCOLOR,
                position: item
              };
            });
            // console.log("选中的坐标数据：", ps)
            setCurPositions(ps);
          } else {
            setCurPositions([]);
          }
        }
      }, 500);
    }
  };

  useEffect(() => {
    if (curFile.fileExtension === "md") {
      const timerMd = setInterval(() => {
        if (mdRef.current) {
          clearInterval(timerMd);
          setTimeout(() => {
            mark();
          }, 100);
        }
      }, 0);
    }
  }, [curChunk]);

  const setPaginationPosition = () => {
    if (pdfBoxRef.current) {
      const el = pdfBoxRef.current as any;
      const parentEl = el.parentElement;
      if (parentEl) {
        const grandpaEl = parentEl.parentElement;
        if (grandpaEl) {
          const clientRect = grandpaEl.getBoundingClientRect();
          const { x, width } = clientRect;
          if (x || width) {
            setPagePosition({
              left: x,
              width: width + 1
            });
          }
        }
      }
    }
  };

  useEffect(() => {
    if (
      pdfBoxRef.current &&
      Object.prototype.toString.call(pdfBoxRef.current) ===
        "[object HTMLDivElement]"
    ) {
      setPaginationPosition();
    }
  }, [pdfBoxRef.current]);

  useEffect(() => {
    const dom = document.getElementById("pdfBox");
    if (dom) {
      setRenderWidth(dom.clientWidth);
    }
  }, []);

  return (
    <div className="chatView h-full" id="pdfBox" ref={pdfBoxRef}>
      {Element}
      {curFile?.fileSuffix === "pdf" && (
        <div
          className="fixed h-10 bg-[#F7F8FC] flex items-center justify-center z-20 select-none"
          style={{
            borderTop: "1px solid #EEEEEE",
            bottom: 0,
            width: `${pagePosition.width}px`,
            // left: `${pagePosition.left}px`,
            right: 0
          }}
        >
          <Pagination
            simple
            defaultCurrent={1}
            total={total}
            pageSize={1}
            size="small"
            current={current}
            onChange={pagiChange}
            showSizeChanger={false}
          />
        </div>
      )}
    </div>
  );
};

export default FileViewNew;
