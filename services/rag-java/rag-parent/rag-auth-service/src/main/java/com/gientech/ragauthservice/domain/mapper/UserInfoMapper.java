package com.gientech.ragauthservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.entity.UserInfoExt;
import com.gientech.ragauthservice.domain.model.UserInfoDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 * <p>
 * 用户表 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-06-13
 */
@Mapper
public interface UserInfoMapper extends BaseMapper<UserInfoDO> {

    int insertBatch(@Param("list") List<UserInfoDO> userInfoDOList);

    int updateBatch(@Param("ids") List<Long> ids, @Param("deptId") String deptId, @Param("deptName") String deptName, @Param("status") Integer status);

    List<UserInfoExt> searchUserList(@Param("deptIds") List<String> deptIds);

    List<UserInfo> listByDeptIds(@Param("deptIds") List<Long> deptIds);

    int updateBatchUserFeature(@Param("userIds") List<Long> userIds, @Param("feature") String feature);

    @Update("UPDATE user_info SET admin_reset_password = null WHERE id = #{userId}")
    int clearAdminResetPassword(Long userId);
}
