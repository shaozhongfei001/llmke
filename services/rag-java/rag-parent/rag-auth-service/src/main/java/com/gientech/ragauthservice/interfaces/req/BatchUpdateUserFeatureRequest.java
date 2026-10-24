package com.gientech.ragauthservice.interfaces.req;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/7/22 16:12
 */
@Data
public class BatchUpdateUserFeatureRequest {
    @NotNull(message = "用户不能为空")
    private List<Long> userIds;
    @NotEmpty(message = "用户特征不能为空")
    private String feature;
}
