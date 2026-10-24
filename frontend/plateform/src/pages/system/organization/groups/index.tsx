import { useState, useEffect } from 'react';
import { GroupList } from './components/GroupList';
import { MemberTable } from './components/MemberTable';
import { GroupInfo } from './types';

import systemApi from '@/apis/system';
import { message } from 'antd';
import SystemContainer from '../../SystemContainer';
import { RequestParams } from '@/apis/system/http-client';

const GroupManagement = () => {
  const [selectedGroup, setSelectedGroup] = useState<GroupInfo | null>(null);
  const [groupList, setGroupList] = useState<GroupInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [frameElements, setFrameElements] = useState<any[]>([]);
  const [frameElementsLoading, setFrameElementsLoading] = useState(false);
  const api = systemApi();

  const fetchGroupList = async () => {
    try {
      setLoading(true);
      const response = await api.getGroupList({pageNo:1,pageSize:9999}as any);
      if (response.data.records) {
        // 按 gmtModified 降序排序
        const sortedGroups = [...response.data.records].sort((a, b) => {
          return new Date(b.gmtModified).getTime() - new Date(a.gmtModified).getTime();
        });
        setGroupList(sortedGroups);
        // 如果当前没有选中的分组，自动选中第一个
        if (!selectedGroup && sortedGroups.length > 0) {
          setSelectedGroup(sortedGroups[0]);
        }
        return sortedGroups;
      }
    } catch (error) {
      console.error('获取分组列表失败:', error);
      message.error('获取分组列表失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchFrameElements = async (groupId: string) => {
    try {
      setFrameElementsLoading(true);
      const params: RequestParams & { query?: any } = {
        query: {
          groupId,
          pageNo: 1,
          pageSize: 9999,
          flatUser: false
        }
      };
      const response = await api.getFrameElements(params);
      if (response.data.records) {
        setFrameElements(response.data.records);
      }
    } catch (error) {
      console.error('获取分组用户信息失败:', error);
      message.error('获取分组用户信息失败');
    } finally {
      setFrameElementsLoading(false);
    }
  };

  useEffect(() => {
    fetchGroupList();
  }, []);

  useEffect(() => {
    if (selectedGroup?.id) {
      fetchFrameElements(selectedGroup.id);
    } else {
      setFrameElements([]);
    }
  }, [selectedGroup?.id]);

  return (
    <SystemContainer title="分组管理" description='你可以创建用户组，并将任意部门或成员添加至一个或多个用户组内，通过和管理后台其他功能结合，实现更灵活的用户管理'>
      <div className="w-full h-full flex">
        {/* 左侧群组列表 */}
        <div className="w-[260px] h-full border-r border-gray-200 border-solid border-t-0 border-l-0 border-b-0">
          <GroupList 
            loading={loading}
            groupList={groupList}
            onSelect={setSelectedGroup}
            selectedGroup={selectedGroup}
            onRefresh={async () => {
              const groups = await fetchGroupList();
              if (groups && groups.length > 0) {
                setSelectedGroup(groups[0]);
              }
            }}
            frameElements={frameElements}
          />
        </div>

        {/* 右侧成员列表 */}
        <div className="flex-1 h-full p-4">
          <MemberTable 
            group={selectedGroup}
            frameElements={frameElements}
            loading={frameElementsLoading}
            onRefresh={fetchFrameElements}
          />
        </div>
      </div>
    </SystemContainer>
  );
};

export default GroupManagement;
