import { useEffect, useState, useMemo, useRef } from "react";
import {
  Timeline,
  Card,
  Select,
  DatePicker,
  Input,
  Spin,
  Row,
  Col,
  Statistic,
  Switch,
  Radio,
  Avatar
} from "antd";
import {
  ClockCircleOutlined,
  UserOutlined,
  GlobalOutlined,
  ApartmentOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  BarChartOutlined,
  UnorderedListOutlined
} from "@ant-design/icons";
import SystemContainer from "../SystemContainer";
import InfiniteScroll from "react-infinite-scroll-component";
import dayjs from "dayjs";
import { Line, Pie } from "@ant-design/plots";
import {
  GRADIENTS,
  getAvatarProps,
  getIconProps,
  getRoundedContainerProps
} from "../organization/config/gradients";

import type { UserOperateRecord } from "@/apis/system/data-contracts";
import { HttpClient } from "@/apis/system/http-client";
import systemApi from "@/apis/system";
const api = systemApi();
import "./style.css";
import { MonitorCog } from "lucide-react";
const { RangePicker } = DatePicker;

interface OperateRecord {
  id: string;
  endTime?: string;
  gmtCreated?: string;
  gmtModified?: string;
  ip: string;
  name: string;
  params?: string;
  startTime?: string;
  success: number;
  url: string;
  userId?: string;
  userName?: string;
}

const operationTypeOptions = [
  { value: "login", label: "登录" },
  { value: "logout", label: "登出" },
  { value: "create", label: "创建" },
  { value: "update", label: "更新" },
  { value: "delete", label: "删除" },
  { value: "query", label: "查询" }
];

const statusColorMap = {
  success: "#52c41a",
  failed: "#ff4d4f"
};

export default function UserOperate() {
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);
  const [records, setRecords] = useState<OperateRecord[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [viewMode, setViewMode] = useState<"timeline" | "statistics">(
    "timeline"
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const [chartHeight, setChartHeight] = useState(0);
  const [filters, setFilters] = useState({
    username: "",
    dateRange: null as [dayjs.Dayjs, dayjs.Dayjs] | null,
    operationType: undefined as string | undefined
  });

  const getOperationTypeLabel = (type: string) => {
    // 从 URL 中提取操作类型
    const urlOperation = type.split("/").pop()?.split("?")[0] || "";
    // 美化显示
    return urlOperation
      .replace(/([A-Z])/g, " $1") // 在大写字母前添加空格
      .replace(/^./, (str) => str.toUpperCase()) // 首字母大写
      .trim();
  };

  const fetchOperateRecords = async (page = 1, isLoadMore = false) => {
    try {
      setLoading(true);
      const { data } = await api.getUserOperateList({
        pageNo: page,
        pageSize: 500,

        fuzzy: filters.username || undefined,
        operationType: filters.operationType,
        start: filters.dateRange?.[0]?.format("YYYY-MM-DD"),
        end: filters.dateRange?.[1]?.format("YYYY-MM-DD")
      });

      console.log("操作记录数据:", data);
      if (data?.records) {
        const formattedRecords: OperateRecord[] = data.records.map(
          (record) => ({
            id: record.id,
            endTime: record.endTime,
            gmtCreated: record.gmtCreated,
            gmtModified: record.gmtModified,
            ip: record.ip,
            name: record.name || "",
            params: record.params,
            startTime: record.startTime,
            success: record.success || 0,
            url: record.url || "",
            userId: record.userId,
            userName: record.userName
          })
        );

        setRecords((prev) =>
          isLoadMore ? [...prev, ...formattedRecords] : formattedRecords
        );
        setTotal(data.total || 0);

        setHasMore(page * 30 < (data.total || 0));
        setCurrentPage(page);
      }
    } catch (error) {
      console.error("获取操作记录失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 加载更多数据
  const loadMore = () => {
    if (!loading && hasMore) {
      fetchOperateRecords(currentPage + 1, true);
    }
  };

  useEffect(() => {
    setCurrentPage(1); // 重置页码
    fetchOperateRecords(1, false);
  }, [filters]);

  useEffect(() => {
    const updateHeight = () => {
      if (containerRef.current) {
        const viewHeight = window.innerHeight;
        const containerTop = containerRef.current.getBoundingClientRect().top;
        const padding = 180;
        setChartHeight(viewHeight - containerTop - padding - 80);
      }
    };

    // 初始加载和窗口大小改变时更新高度
    updateHeight();
    window.addEventListener("resize", updateHeight);

    // 视图模式改变时也要更新高度
    const timer = setTimeout(updateHeight, 100);

    return () => {
      window.removeEventListener("resize", updateHeight);
      clearTimeout(timer);
    };
  }, [viewMode]); // 添加 viewMode 作为依赖

  // 统计数据
  const statistics = useMemo(() => {
    const statusCount = records.reduce(
      (acc, record) => {
        const status = record.success ? "success" : "failed";
        acc[status] = (acc[status] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

    // 计算数据的时间范围
    const timestamps = records.map((record) =>
      dayjs(record.startTime || record.gmtCreated).valueOf()
    );
    const minTime = Math.min(...timestamps);
    const maxTime = Math.max(...timestamps);
    const timeRange = maxTime - minTime;

    // 计算5个时间区间
    const intervalCount = 5;
    const intervalSize = timeRange / (intervalCount - 1);

    // 按时间和操作名称分组，统计调用次数
    const timeSeriesData = records.reduce(
      (acc, record) => {
        const timestamp = dayjs(
          record.startTime || record.gmtCreated
        ).valueOf();
        const intervalIndex = Math.floor((timestamp - minTime) / intervalSize);
        const intervalStart = dayjs(minTime + intervalIndex * intervalSize);
        const timeStr = intervalStart.format("MM-DD HH:mm");
        const name = record.name || "未知操作";
        const key = `${timeStr}-${name}`;

        if (!acc[key]) {
          acc[key] = {
            time: timeStr,
            name: name,
            value: 1,
            users: [
              {
                username: record.userName || "未知用户",
                count: 1
              }
            ]
          };
        } else {
          acc[key].value += 1;
          const userIndex = acc[key].users.findIndex(
            (u) => u.username === (record.userName || "未知用户")
          );
          if (userIndex >= 0) {
            acc[key].users[userIndex].count += 1;
          } else {
            acc[key].users.push({
              username: record.userName || "未知用户",
              count: 1
            });
          }
        }
        return acc;
      },
      {} as Record<
        string,
        {
          time: string;
          name: string;
          value: number;
          users: Array<{ username: string; count: number }>;
        }
      >
    );

    // 转换为数组并按时间排序
    const sortedTimeSeriesData = Object.values(timeSeriesData).sort(
      (a, b) => dayjs(a.time).valueOf() - dayjs(b.time).valueOf()
    );

    console.log("处理后的数据:", sortedTimeSeriesData);

    return {
      statusCount,
      timeSeriesData: sortedTimeSeriesData
    };
  }, [records]);

  const formatParams = (params: string) => {
    try {
      // 尝试解析 JSON
      let parsed;
      if (params.startsWith("[") || params.startsWith("{")) {
        parsed = JSON.parse(params);
      } else {
        // 如果不是标准JSON格式，尝试解析括号内的内容
        const match = params.match(/\((.*)\)/);
        if (match) {
          // 将键值对格式转换为对象
          const obj: { [key: string]: string } = {};
          match[1].split(", ").forEach((pair) => {
            const [key, value] = pair.split("=");
            if (key && value !== undefined) {
              obj[key] = value;
            }
          });
          parsed = obj;
        } else {
          return params;
        }
      }

      // 自定义格式化输出
      const formatValue = (value: any): string => {
        if (value === null) return "null";
        if (value === undefined) return "undefined";
        if (Array.isArray(value)) {
          return `[\n${value.map((v) => `    ${formatValue(v)}`).join(",\n")}\n]`;
        }
        if (typeof value === "object") {
          return `{\n${Object.entries(value)
            .map(([k, v]) => `    ${k}: ${formatValue(v)}`)
            .join(",\n")}\n}`;
        }
        return value.toString();
      };

      return formatValue(parsed);
    } catch (e) {
      // 如果解析失败，返回原始字符串
      return params;
    }
  };

  const formatDateTime = (dateTimeStr: string | undefined) => {
    if (!dateTimeStr) return null;
    const dt = dayjs(dateTimeStr);
    return (
      <div className="text-gray-500 text-xs">
        <div>{dt.format("YYYY-MM-DD")}</div>
        <div>{dt.format("HH:mm:ss")}</div>
      </div>
    );
  };

  const renderTimeline = () => (
    <div
      id="scrollableDiv"
      className="userOperate"
      style={{
        height: "calc(100vh - 300px)",
        overflow: "auto",
        padding: "0 16px"
      }}
    >
      <InfiniteScroll
        dataLength={records.length}
        next={loadMore}
        hasMore={hasMore}
        loader={
          <div className="text-center py-4">
            <Spin />
          </div>
        }
        scrollableTarget="scrollableDiv"
        endMessage={
          <div className="text-center text-gray-500 py-4">没有更多数据了</div>
        }
      >
        <Timeline
          mode="left"
          style={{ padding: "0 8px" }}
          items={records.map((record) => ({
            color: record.success ? "green" : "red",
            label: formatDateTime(record.startTime || record.gmtCreated),
            children: (
              <div
                key={record.id}
                className="bg-white p-4 rounded-lg shadow-sm mb-4 hover:shadow-md transition-shadow ml-2"
              >
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center">
                    <Avatar
                      icon={<UserOutlined {...getIconProps()} />}
                      {...getAvatarProps("MEMBER")}
                    />
                    <span className="font-medium mr-4">
                      {record.userName || "未知用户"}
                    </span>
                    <span className="text-gray-400 flex items-center">
                      <div
                        {...getRoundedContainerProps("GROUP")}
                        className="w-6 h-6 flex items-center justify-center mr-1"
                      >
                        <GlobalOutlined
                          {...getIconProps()}
                          className="text-white text-xs"
                        />
                      </div>
                      {record.ip}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="mr-4 flex items-center">
                      <div className="w-6 h-6 flex items-center justify-center">
                        <MonitorCog {...getIconProps()} className=" text-xs" />
                      </div>
                      <span className="font-medium">
                        {record.name || getOperationTypeLabel(record.url)}
                      </span>
                    </div>
                    <div
                      className={`flex items-center ${
                        record.success ? "text-green-500" : "text-red-500"
                      }`}
                    >
                      <div className="w-6 h-6 flex items-center justify-center  rounded-lg">
                        {record.success === 1 ? (
                          <CheckCircleOutlined
                            style={{
                              color:
                                record.success === 1
                                  ? "linear-gradient(135deg, #22C55E 0%, #16A34A 100%)"
                                  : "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
                            }}
                            className=" text-xs"
                          />
                        ) : (
                          <CloseCircleOutlined
                            style={{
                              color:
                                record.success === 1
                                  ? "linear-gradient(135deg, #22C55E 0%, #16A34A 100%)"
                                  : "linear-gradient(135deg, #EF4444 0%, #DC2626 100%)"
                            }}
                            className=" text-xs"
                          />
                        )}
                      </div>
                      <span>
                        {record.success === 1 ? "操作成功" : "操作失败"}
                      </span>
                    </div>
                  </div>
                </div>

                {record.params && (
                  <div className="mt-3 text-gray-500 text-sm bg-gray-50 p-3 rounded">
                    <div className="font-medium mb-2">请求参数：</div>
                    <div className="whitespace-pre font-mono text-xs overflow-x-auto bg-white p-2 rounded border border-gray-100">
                      {formatParams(record.params)}
                    </div>
                  </div>
                )}

                {record.url && (
                  <div className="mt-2 text-gray-400 text-xs">
                    <span className="font-medium">请求路径：</span>
                    {record.url}
                  </div>
                )}
              </div>
            )
          }))}
        />
      </InfiniteScroll>
    </div>
  );

  const renderStatistics = () => {
    const lineData = statistics.timeSeriesData;

    return (
      <div className="space-y-6" ref={containerRef}>
        <Row gutter={16}>
          <Col span={8}>
            <Card>
              <Statistic title="总操作次数" value={total} suffix="次" />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="成功率"
                value={
                  ((statistics.statusCount.success || 0) / records.length) * 100
                }
                precision={2}
                suffix="%"
                valueStyle={{ color: "#3f8600" }}
              />
            </Card>
          </Col>
          <Col span={8}>
            <Card>
              <Statistic
                title="失败率"
                value={
                  ((statistics.statusCount.failed || 0) / records.length) * 100
                }
                precision={2}
                suffix="%"
                valueStyle={{ color: "#cf1322" }}
              />
            </Card>
          </Col>
        </Row>

        <Card
          title={
            <div className="flex items-center gap-2">
              <div {...getRoundedContainerProps("GROUP")} className="w-8 h-8">
                <MonitorCog {...getIconProps()} className="text-white" />
              </div>
              <span>操作趋势</span>
              <span className="text-gray-500 text-xs">
                原始记录数据({records.length}条)
              </span>
            </div>
          }
          styles={{ body: { minHeight: `${chartHeight}px` } }}
        >
          <Line
            data={lineData}
            xField="time"
            yField="value"
            seriesField="name"
            height={chartHeight - 60}
            point={{
              size: 4,
              shape: "circle",
              style: {
                fillOpacity: 1
              }
            }}
            xAxis={{
              type: "cat",
              tickCount: 5,
              label: {
                autoRotate: true,
                autoHide: false,
                autoEllipsis: true,
                style: {
                  fontSize: 12
                }
              }
            }}
            yAxis={{
              label: {
                formatter: (v: number) => `${v}次`,
                style: {
                  fontSize: 12
                }
              }
            }}
            legend={{
              position: "top",
              itemName: {
                style: {
                  fontSize: 12
                }
              }
            }}
            smooth={true}
            animation={{
              appear: {
                animation: "wave-in",
                duration: 1000
              }
            }}
            // tooltip={{
            //   showMarkers: true,
            //   shared: true,
            //   showCrosshairs: true,
            //   crosshairs: {
            //     type: "xy"
            //   },
            //   domStyles: {
            //     "g2-tooltip": {
            //       padding: "8px",
            //       backgroundColor: "#fff",
            //       boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
            //       borderRadius: "4px"
            //     }
            //   },
            //   customContent: (
            //     title: string,
            //     items: {
            //       data: {
            //         time: string;
            //         name: string;
            //         users: Array<{ username: string; count: number }>;
            //         value: number;
            //       };
            //       color: string;
            //     }[]
            //   ) => {
            //     if (!items || items.length <= 0) return null;
            //     const item = items[0];
            //     const { time, name, users, value } = item.data;
            //     return (
            //       <div style={{ padding: "8px 0" }}>
            //         <div
            //           style={{
            //             color: "#595959",
            //             fontWeight: 600,
            //             marginBottom: "12px",
            //             display: "flex",
            //             alignItems: "center",
            //             gap: "8px"
            //           }}
            //         >
            //           <span
            //             style={{
            //               display: "inline-block",
            //               width: "8px",
            //               height: "8px",
            //               borderRadius: "50%",
            //               backgroundColor: item.color
            //             }}
            //           ></span>
            //           {name}
            //         </div>
            //         <div
            //           style={{
            //             color: "#8c8c8c",
            //             fontSize: "12px",
            //             marginBottom: "8px"
            //           }}
            //         >
            //           {time}
            //         </div>
            //         <div
            //           style={{
            //             borderTop: "1px solid #e8e8e8",
            //             paddingTop: "8px",
            //             marginTop: "8px"
            //           }}
            //         >
            //           <div style={{ marginBottom: "4px" }}>
            //             总调用次数：
            //             <span style={{ color: "#1677ff", fontWeight: 500 }}>
            //               {value}次
            //             </span>
            //           </div>
            //           <div style={{ fontSize: "12px" }}>
            //             <div style={{ marginBottom: "4px", color: "#8c8c8c" }}>
            //               调用详情：
            //             </div>
            //             {users.map(
            //               (
            //                 user: { username: string; count: number },
            //                 index: number
            //               ) => (
            //                 <div
            //                   key={index}
            //                   style={{
            //                     display: "flex",
            //                     justifyContent: "space-between",
            //                     padding: "2px 0"
            //                   }}
            //                 >
            //                   <span style={{ color: "#262626" }}>
            //                     {user.username}
            //                   </span>
            //                   <span
            //                     style={{ color: "#1677ff", marginLeft: "24px" }}
            //                   >
            //                     {user.count}次
            //                   </span>
            //                 </div>
            //               )
            //             )}
            //           </div>
            //         </div>
            //       </div>
            //     );
            //   }
            // }}
          />
        </Card>
      </div>
    );
  };

  return (
    <SystemContainer title="用户操作记录" description="记录用户操作行为和结果">
      <Card>
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex gap-4 mb-6 flex-1">
            <Input
              placeholder="搜索用户"
              prefix={<UserOutlined />}
              style={{ width: 200 }}
              value={filters.username}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, username: e.target.value }))
              }
            />
            <RangePicker
              style={{ width: 300 }}
              onChange={(dates) => {
                if (dates) {
                  setFilters((prev) => ({
                    ...prev,
                    dateRange: dates as [dayjs.Dayjs, dayjs.Dayjs]
                  }));
                } else {
                  setFilters((prev) => ({ ...prev, dateRange: null }));
                }
              }}
            />
          </div>
          <Radio.Group
            value={viewMode}
            onChange={(e) => {
              setViewMode(e.target.value);
              // 切换视图后，给一个短暂的延时让 DOM 更新
              setTimeout(() => {
                if (containerRef.current) {
                  const viewHeight = window.innerHeight;
                  const containerTop =
                    containerRef.current.getBoundingClientRect().top;
                  const padding = 180;
                  setChartHeight(viewHeight - containerTop - padding);
                }
              }, 100);
            }}
            style={{ marginBottom: 8 }}
          >
            <Radio.Button value="timeline">
              <UnorderedListOutlined /> 时间轴
            </Radio.Button>
            <Radio.Button value="statistics">
              <BarChartOutlined /> 统计图
            </Radio.Button>
          </Radio.Group>
        </div>

        <div style={{ minHeight: chartHeight }}>
          {viewMode === "statistics" ? renderStatistics() : renderTimeline()}
        </div>
      </Card>
    </SystemContainer>
  );
}
