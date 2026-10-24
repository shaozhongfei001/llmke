package com.gientech.ragcommon.infrastructure.template;

import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** 创造树的模板方法
 * @author chenjuan
 * @date 2025/5/19 17:26
 */
public abstract class TreeBuilder<T> {
    public List<T> buildTree(List<T> elements) {
        Map<Long, T> elementMap = new HashMap<>();
        List<T> rootElements = new ArrayList<>();
        if (CollectionUtils.isEmpty(elements)) {
            return List.of();
        }

        for (T element : elements) {
            Long id = getId(element);
            elementMap.put(id, element);

            if (isRoot(element)) {
                rootElements.add(element);
            }
        }

        return createRelations(elements, elementMap, rootElements);
    }

    protected abstract Long getId(T element);

    protected abstract boolean isRoot(T element);

    protected abstract List<T> createRelations(
            List<T> elements,
            Map<Long, T> elementMap,
            List<T> rootElements
    );
}
