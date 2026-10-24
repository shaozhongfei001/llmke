package com.gientech.ragcommon.context.user;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@NoArgsConstructor
@AllArgsConstructor
@Builder
@Data
public class User {

    private String userId;

    private String userName;

    private String appKey;

    private String apiKey;

    public User(String userId, String userName) {
        this.userId = userId;
        this.userName = userName;
    }
}
