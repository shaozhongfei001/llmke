
export default function SystemLoading() {
  return (
    <div className="flex justify-start items-start ml-5 flex-col h-full w-[98%] relative">
      {/* 标题和描述骨架 */}
      <div className="flex h-[42px] z-10 bg-transparent gap-x-2 pb-2 flex-row items-center justify-start w-full">
        <div className="h-5 w-32 bg-gray-200 animate-pulse rounded"></div>
        <div className="h-4 w-48 bg-gray-100 animate-pulse rounded"></div>
      </div>
      
      {/* 内容区域骨架 */}
      <div className="flex flex-col h-auto w-full bg-white border border-white/20 shadow-sm rounded-md p-4">
        {/* 多行内容骨架 */}
        <div className="space-y-4">
          <div className="h-4 bg-gray-200 animate-pulse rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 animate-pulse rounded w-full"></div>
          <div className="h-4 bg-gray-200 animate-pulse rounded w-5/6"></div>
          <div className="h-4 bg-gray-200 animate-pulse rounded w-2/3"></div>
          
          {/* 区块内容骨架 */}
          <div className="mt-6 space-y-3">
            <div className="h-24 bg-gray-100 animate-pulse rounded w-full"></div>
            <div className="h-24 bg-gray-100 animate-pulse rounded w-full"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
