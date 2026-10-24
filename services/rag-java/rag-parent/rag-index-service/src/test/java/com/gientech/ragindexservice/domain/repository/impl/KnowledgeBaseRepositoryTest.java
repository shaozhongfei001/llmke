package com.gientech.ragindexservice.domain.repository.impl;

import com.gientech.ragindexservice.domain.repository.KnowledgeBaseRepository;
import org.checkerframework.checker.units.qual.A;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * @author chenjuan
 * @date 2025/3/12 11:43
 */
@SpringBootTest
public class KnowledgeBaseRepositoryTest {

    @Autowired
    private KnowledgeBaseRepository knowledgeBaseRepository;
    @Test
    public void test() {
        knowledgeBaseRepository.getHighestPermission(1536L,1L,1248L,"chenjuan");
    }
}
