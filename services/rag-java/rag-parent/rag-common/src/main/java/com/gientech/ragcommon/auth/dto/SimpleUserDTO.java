package com.gientech.ragcommon.auth.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Objects;

/**
 * @author chenjuan
 * @date 2025/3/24 15:06
 */
@Data
public class SimpleUserDTO {

    private String userName;

    private String userRealname;

    private String userEmail;

    private Long id;

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        SimpleUserDTO that = (SimpleUserDTO) o;
        return Objects.equals(userName, that.userName) && Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(userName, id);
    }
}
