package com.gientech.ragauthservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.date.DateUtil;
import com.alibaba.excel.support.ExcelTypeEnum;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.application.helper.DeptImportExportHelper;
import com.gientech.ragauthservice.application.service.DepartmentInfoAppService;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragauthservice.domain.entity.GroupInfo;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.service.DepartmentInfoDomainService;
import com.gientech.ragauthservice.domain.service.GroupInfoDomainService;
import com.gientech.ragauthservice.domain.service.UserInfoDomainService;
import com.gientech.ragauthservice.infrastructure.convertor.DepartmentInfoConvertor;
import com.gientech.ragauthservice.infrastructure.convertor.UserInfoConvertor;
import com.gientech.ragcommon.auth.dto.DepartmentInfoDTO;
import com.gientech.ragcommon.auth.dto.DeptImportExportDTO;
import com.gientech.ragcommon.auth.dto.FrameElement;
import com.gientech.ragcommon.auth.enums.FrameElementTypeEnums;
import com.gientech.ragcommon.auth.enums.UserStatusEnum;
import com.gientech.ragcommon.auth.request.CreateDepartmentInfoReq;
import com.gientech.ragcommon.auth.request.ListDepartmentInfoReq;
import com.gientech.ragcommon.auth.request.UpdateDepartmentInfoReq;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.start.easyexcel.result.ExcelImportResult;
import com.gientech.start.redisson.utils.RedissonUtils;
import com.google.common.collect.Maps;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.compress.utils.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.web.multipart.MultipartFile;

import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

@Slf4j
@Service
public class DepartmentInfoAppServiceImpl implements DepartmentInfoAppService {

    @Autowired
    private DepartmentInfoDomainService departmentInfoDomainService;

    @Autowired
    private final UserInfoDomainService userInfoDomainService;

    @Autowired
    private GroupInfoDomainService groupInfoDomainService;

    @Autowired
    private DeptImportExportHelper deptImportExportHelper;

    @Autowired
    private RedissonUtils redissonUtils;

    private final static Long DEPT_IMPORT_DATA_ERROR_EXPIRE = 3L;

    public DepartmentInfoAppServiceImpl(UserInfoDomainService userInfoDomainService) {
        this.userInfoDomainService = userInfoDomainService;
    }

    @Override
    public DepartmentInfoDTO findById(Long id) throws ApplicationException {
        if (Objects.isNull(id) || id <= 0)
            throw new ApplicationException(ErrCodeEnum.PARAM_ILLEGAL.getErrCode(), "参数不能为空，且必须是正整数");
        try {
            DepartmentInfo byId = departmentInfoDomainService.findById(id);
            return BeanUtil.copyProperties(byId, DepartmentInfoDTO.class);
        } catch (Exception e) {
            throw new ApplicationException(ErrCodeEnum.DEPARTMENT_QUERY_ERROR);
        }
    }

    @Override
    public Boolean create(CreateDepartmentInfoReq departmentInfoReq) throws ApplicationException {
        try {
            return departmentInfoDomainService.create(BeanUtil.copyProperties(departmentInfoReq, DepartmentInfo.class));
        } catch (DomainException e) {
            log.error("error", e);
            throw new ApplicationException(e.getErrCode(), e.getMessage());
        } catch (Exception e) {
            log.error("error", e);
            throw new ApplicationException(ErrCodeEnum.DEPARTMENT_CREATE_ERROR);
        }
    }

    @Override
    public Boolean edit(UpdateDepartmentInfoReq departmentInfoReq) {
        try {
            return departmentInfoDomainService.edit(BeanUtil.copyProperties(departmentInfoReq, DepartmentInfo.class));
        } catch (DomainException e) {
            throw new ApplicationException(e.getErrCode(), e.getMessage());
        } catch (Exception e) {
            throw new ApplicationException(ErrCodeEnum.DEPARTMENT_EDIT_ERROR);
        }
    }

    @Override
    public Page<DepartmentInfoDTO> list(ListDepartmentInfoReq listDepartmentInfoReq) throws ApplicationException {
        try {
            Page<DepartmentInfo> departmentInfoPage = departmentInfoDomainService.list(listDepartmentInfoReq);
            Page<DepartmentInfoDTO> result = new Page<>();
            BeanUtil.copyProperties(departmentInfoPage, result);
            List<DepartmentInfoDTO> departmentInfoDTOS = BeanUtil.copyToList(departmentInfoPage.getRecords(), DepartmentInfoDTO.class);
            result.setRecords(departmentInfoDTOS);
            return result;
        } catch (Exception e) {
            throw new ApplicationException(ErrCodeEnum.DEPARTMENT_QUERY_ERROR);
        }
    }

    @Override
    public Boolean deleteById(Long id) throws ApplicationException {
        if (Objects.isNull(id) || id <= 0)
            throw new ApplicationException(ErrCodeEnum.PARAM_ILLEGAL.getErrCode(), "参数不能为空，且必须是正整数");
        try {
            return departmentInfoDomainService.deleteById(id);
        } catch (Exception e) {
            throw new ApplicationException(ErrCodeEnum.DEPARTMENT_DELETE_ERROR);
        }
    }

    @Override
    public Boolean recursiveDeleteByIds(List<Long> ids) throws ApplicationException {
        if (CollectionUtils.isEmpty(ids)) {
            throw new ApplicationException(ErrCodeEnum.PARAM_LIST_EMPTY);
        }
        return departmentInfoDomainService.recursiveDeleteByIds(ids);
    }

    @Override
    public List<FrameElement> frameSearch(ListDepartmentInfoReq req) {
        List<FrameElement> fuzzyDepartments = getAllDepartmentInfo(req.getFuzzy());

        List<FrameElement> fuzzyUsers = getFuzzyUsers(req.getFuzzy());

        List<FrameElement> fuzzyGroups = getFuzzyGroups(req.getFuzzy());


        List<FrameElement> fuzzyResult = Lists.newArrayList();
        fuzzyResult.addAll(fuzzyDepartments);
        fuzzyResult.addAll(fuzzyUsers);
        fuzzyResult.addAll(fuzzyGroups);

        return fuzzyResult;
    }

    private List<FrameElement> getFuzzyGroups(String fuzzy) {
        List<GroupInfo> groupInfos = groupInfoDomainService.list(fuzzy, 1L, 9999L).getRecords();
        return groupInfos.stream()
                .map(groupInfo -> FrameElement.builder().id(groupInfo.getId()).name(groupInfo.getName()).elementType(FrameElementTypeEnums.GROUP).build())
                .collect(Collectors.toList());
    }

    private List<FrameElement> getFuzzyUsers(String fuzzy) {
        List<UserInfo> userInfos = userInfoDomainService.list(fuzzy);
        List<FrameElement> frameElements = UserInfoConvertor.INSTANCE.userInfoS2FrameElements(userInfos);
        frameElements.forEach(element -> element.setElementType(FrameElementTypeEnums.USER));
        return frameElements;
    }

    @Override
    public List<FrameElement> treeFrame() {
        List<FrameElement> treeList = Lists.newArrayList();
        List<FrameElement> departments = getFrameDepartments(null, true, null);
        List<FrameElement> users = getFrameUsers();
        treeList.addAll(departments);
        treeList.addAll(users);
        return treeList;
    }

    @Override
    public List<FrameElement> treeFrameByDeptId(Long deptId) {
        return getFrameDepartments(deptId, true, null);
    }

    @Override
    public List<FrameElement> treeFrameByDeptIds(List<Long> deptIds) {
        if (CollectionUtils.isEmpty(deptIds)) {
            return Lists.newArrayList();
        }
        return getFrameDepartmentsByDeptIds(deptIds);
    }

    @Override
    public List<FrameElement> treeDeptById(Long deptId, Integer depth) {
        return getFrameDepartments(deptId, false, depth);
    }


    private List<FrameElement> getFrameUsers() {
        List<UserInfo> userInfos = userInfoDomainService.listNoDeptUsers(UserInfo.builder().deptId(null).build());
        List<FrameElement> userFrameElements = BeanUtil.copyToList(userInfos, FrameElement.class);
        userFrameElements.forEach(frameElement -> frameElement.setElementType(FrameElementTypeEnums.USER));
        return userFrameElements;
    }


    private List<FrameElement> getFrameDepartments(Long deptId, boolean withUsers, Integer depth) {
        List<FrameElement> departments = getDepartmentsByDeptId(deptId, depth);
        Map<Long, FrameElement> departmentMap = Maps.newHashMap();
        List<FrameElement> rootDepartments = Lists.newArrayList();

        departments.forEach(department -> {
            departmentMap.put(department.getId(), department);
            if (department.getParentId() == null || (Objects.nonNull(deptId) && deptId.equals(department.getId()))) {
                rootDepartments.add(department);
            }
        });
        //设置父子关系
        return createRelations(withUsers, departments, departmentMap, rootDepartments, UserStatusEnum.ENABLED.getCode());
    }


    private List<FrameElement> getFrameDepartmentsByDeptIds(List<Long> deptIds) {

        Map<Long, FrameElement> departmentMap = Maps.newHashMap();
        List<FrameElement> rootDepartments = Lists.newArrayList();
        List<FrameElement> departments = getFlatDepartments(deptIds, departmentMap, rootDepartments);
        //设置父子关系
        return createRelations(true, departments, departmentMap, rootDepartments, UserStatusEnum.ENABLED.getCode());
    }

    private List<FrameElement> getFlatDepartments(List<Long> deptIds, Map<Long, FrameElement> departmentMap, List<FrameElement> rootDepartments) {
        List<FrameElement> departments = CollectionUtils.isEmpty(deptIds) ? getAllDepartmentInfo(null) : getDepartmentsByDeptId(deptIds);
        departments.forEach(department -> {
            departmentMap.put(department.getId(), department);
            if (department.getParentId() == null || (!CollectionUtils.isEmpty(deptIds) && deptIds.contains(department.getId()))) {
                rootDepartments.add(department);
            }
        });
        return departments;
    }

    private List<FrameElement> getFlatDepartmentsByDeptIds(List<Long> deptIds) {
        Map<Long, FrameElement> departmentMap = Maps.newHashMap();
        List<FrameElement> rootDepartments = Lists.newArrayList();
        List<FrameElement> departments = getFlatDepartments(deptIds, departmentMap, rootDepartments);
        //设置父子关系
        createRelations(false, departments, departmentMap, rootDepartments, null);
        return departments;
    }

    /**
     * @param withUsers
     * @param departments
     * @param departmentMap
     * @param rootDepartments
     * @param status          status为null，则查询除了离职状态之外的，如果status为具体的值，则查具体的值
     * @return
     */
    private List<FrameElement> createRelations(boolean withUsers, List<FrameElement> departments, Map<Long, FrameElement> departmentMap, List<FrameElement> rootDepartments, Integer status) {
        departments.forEach(department -> {
            //设置元素类型
            department.setElementType(FrameElementTypeEnums.DEPARTMENT);
            if (Objects.nonNull(department.getParentId())) {
                FrameElement frameElement = departmentMap.get(department.getParentId());
                setUsers(withUsers, department, status);
                if (Objects.nonNull(frameElement)) {
                    if (CollectionUtils.isEmpty(frameElement.getChildren())) {
                        frameElement.setChildren(Lists.newArrayList());
                    }
                    department.setParentDeptName(frameElement.getName());
                    frameElement.getChildren().add(department);
                }
            }
        });
        rootDepartments.forEach(department -> {
            Optional.ofNullable(departmentInfoDomainService.findById(department.getParentId()))
                    .map(DepartmentInfo::getName)
                    .ifPresent(department::setParentDeptName);
            setUsers(withUsers, department, status);
        });
        return rootDepartments;
    }

    private void setUsers(boolean withUsers, FrameElement department, Integer userStatus) {
        List<FrameElement> userList = getUserList(department, userStatus);
        if (!CollectionUtils.isEmpty(userList)) {
            if (withUsers) {
                if (!CollectionUtils.isEmpty(department.getChildren())) {
                    department.getChildren().addAll(userList);
                } else {
                    department.setChildren(userList);
                }
            }
            department.setUserCount(userList.size());
        }
    }

    private List<FrameElement> getAllDepartmentInfo(String fuzzy) {
        ListDepartmentInfoReq req = ListDepartmentInfoReq.builder().pageNo(1L).pageSize(999L).fuzzy(fuzzy).build();
        Page<DepartmentInfo> list = departmentInfoDomainService.list(req);
        List<FrameElement> departments = DepartmentInfoConvertor.INSTANCE.departmentInfos2FrameElements(list.getRecords());
        departments.forEach(department -> department.setElementType(FrameElementTypeEnums.DEPARTMENT));
        return departments;
    }

    private List<FrameElement> getDepartmentsByDeptId(Long deptId, Integer depth) {
        List<DepartmentInfo> list = departmentInfoDomainService.recursiveListById(deptId, depth);
        return DepartmentInfoConvertor.INSTANCE.departmentInfos2FrameElements(list);
    }

    private List<FrameElement> getDepartmentsByDeptId(List<Long> deptIds) {
        List<DepartmentInfo> list = departmentInfoDomainService.recursiveListByIds(deptIds);
        return BeanUtil.copyToList(list, FrameElement.class);
    }


    private List<FrameElement> getUserList(FrameElement department, Integer status) {
        List<UserInfo> userInfos = userInfoDomainService.list(UserInfo.builder().deptId(String.valueOf(department.getId())).status(status).build());
        List<FrameElement> frameElements = BeanUtil.copyToList(userInfos, FrameElement.class);
        frameElements.forEach(frameElement -> {
            frameElement.setElementType(FrameElementTypeEnums.USER);
            frameElement.setDeptName(department.getName());
        });
        return frameElements;
    }

    @Override
    public void downloadTemplate(ExcelTypeEnum type, HttpServletResponse response) {
        deptImportExportHelper.exportData("部门信息模板", null, DeptImportExportDTO.class, type, response);
    }

    @Override
    public ExcelImportResult<DeptImportExportDTO> importData(MultipartFile file) {
        List<DepartmentInfo> deptList = Lists.newArrayList();
        List<DeptImportExportDTO> failList = Lists.newArrayList();
        ExcelImportResult<DeptImportExportDTO> deptImportExportDTOExcelImportResult = deptImportExportHelper.importData(file, DeptImportExportDTO.class, deptList, failList);
        if (CollectionUtils.isEmpty(deptImportExportDTOExcelImportResult.getFailList())) {
            deptImportExportDTOExcelImportResult.setFailList(failList);
            User user = UserContext.getUser();
            String userName = user.getUserName();
            redissonUtils.set(RedisKeyEnums.DEPT_IMPORT_DATA_ERROR_PREFIX + userName, JSON.toJSONString(failList), DEPT_IMPORT_DATA_ERROR_EXPIRE, TimeUnit.HOURS);
        }
        return deptImportExportDTOExcelImportResult;
    }

    @Override
    public void export(List<Long> pids, HttpServletResponse response) {
        List<FrameElement> deptList = getFlatDepartmentsByDeptIds(pids);
        if (CollectionUtils.isEmpty(deptList)) {
            log.warn("没有数据");
            return;
        }
        deptImportExportHelper.exportData(
                "部门信息" + DateUtil.format(new Date(), "yyyyMMddHHmmss"),
                DepartmentInfoConvertor.INSTANCE.frameElements2DeptImportExportDTOs(deptList),
                DeptImportExportDTO.class,
                ExcelTypeEnum.valueOf("xlsx".toUpperCase(Locale.ROOT)),
                response);
    }

    @Override
    public void exportError(HttpServletResponse response) {
        String deptStr = redissonUtils.get(RedisKeyEnums.DEPT_IMPORT_DATA_ERROR_PREFIX + UserContext.getUser().getUserName());
        List<DeptImportExportDTO> userImportDTOS = JSONArray.parseArray(deptStr, DeptImportExportDTO.class);
        if (CollectionUtils.isEmpty(userImportDTOS))
            return;

        deptImportExportHelper.exportData(
                "导入失败的部门数据" + DateUtil.format(new Date(), "yyyyMMddHHmmss"),
                userImportDTOS,
                DeptImportExportDTO.class,
                ExcelTypeEnum.valueOf("xlsx".toUpperCase(Locale.ROOT)),
                response);
    }
}
