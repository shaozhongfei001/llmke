export const handleReqOrder = (
  reqArr: {
    sectionId: string;
    title: string;
  }[],
  hasDependency: {
    [key: string]: string[];
  }
) => {
  const newReqArr: any[] = [];
  // 用于记录已经处理过的节点，确保每个节点只被检测和排序一次，避免重复处理。
  const visited = new Set<string>();
  // 用于记录当前递归路径中的节点，用来检测是否存在循环依赖。
  // 如果在递归过程中再次访问到某个节点，说明存在循环依赖。
  const tempVisited = new Set<string>();

  //   监测是否有环
  const hasCycle = (sectionId: string): boolean => {
    if (tempVisited.has(sectionId)) return true; // 检测到循环依赖
    if (visited.has(sectionId)) return false; // 已经被依赖，存在于列表中，直接返回

    tempVisited.add(sectionId);
    const dependencies = hasDependency[sectionId] || [];
    for (const dep of dependencies) {
      if (hasCycle(dep)) return true;
    }
    tempVisited.delete(sectionId);
    visited.add(sectionId);
    return false;
  };

  const sortDependencies = (sectionId: string) => {
    if (newReqArr.find((item) => item.sectionId === sectionId)) return; // 已排序
    const dependencies = hasDependency[sectionId] || [];
    for (const dep of dependencies) {
      if (!reqArr.find((item) => item.sectionId === dep)) continue; // 忽略不存在的依赖项
      sortDependencies(dep);
    }
    const item = reqArr.find((item) => item.sectionId === sectionId);
    if (item) newReqArr.push(item);
  };

  for (const item of reqArr) {
    const { sectionId } = item;
    if (!hasCycle(sectionId)) {
      sortDependencies(sectionId);
    } else {
      // 如果存在循环依赖，仍然保留当前项
      newReqArr.push(item);
    }
  }
  console.log("newReqArr", newReqArr);
  return newReqArr;
};
