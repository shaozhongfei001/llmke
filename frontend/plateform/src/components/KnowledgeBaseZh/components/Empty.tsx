import { useMemo } from "react"
// import { Button } from "antd"
import "@/assets/styles/knowledgebase.less"
import { konwledgeTitles, ITabs } from "@/const/knowledgebase"
import EmpetBg from "@/assets/knowledgebase/bg-empty.svg"

interface IEmpty {
  currentTab: number
  onCreateClick: () => void
}

const Empty = (props: IEmpty) => {
  const { currentTab } = props
  const renderBg = () => <img src={EmpetBg} width={106} height={96.5} />
  const renderInfo = useMemo(() => {
    const item = konwledgeTitles.find((item: ITabs) => item.key === currentTab)
    switch (currentTab) {
      case konwledgeTitles[0].key:
        return (
          <div className="empty-my">
            <div className="empty-label">暂无数据</div>
            {/* <div className="empty-label">暂无知识库</div>
            <div className="empty-btn">
              <span>请创建你的知识库</span>
              <Button
                type="link"
                style={{
                  border: "1px solid #014DDF",
                  fontSize: "14px",
                  color: "#014DDF",
                  height: "25px",
                  width: "90px",
                  textAlign: "center",
                }}
                onClick={onCreateClick}
              >
                立即创建
              </Button>
            </div> */}
          </div>
        )
      default:
        return <div className="empty-text">暂无{item ? item.label : ""}</div>
    }
  }, [currentTab])

  return (
    <div className="empty-wrap">
      <div className="empty-bg">
        {renderBg()}
        {renderInfo}
      </div>
    </div>
  )
}

export default Empty
