package com.gientech.tools.database.infrastructure.util;

import cn.hutool.core.text.NamingCase;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONConfig;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;

public class JsonNamingConvertUtil {
    /**
     * 将两层结构的JSON字符串从驼峰命名转换为下划线命名
     * @param jsonStr 原始JSON字符串
     * @return 转换后的JSON字符串
     */
    public static String convertJsonString(String jsonStr) {
        if (JSONUtil.isJsonArray(jsonStr)) {
            // 处理JSON数组
            JSONArray jsonArray = JSONUtil.parseArray(jsonStr);
            JSONArray resultArray = new JSONArray();

            for (Object obj : jsonArray) {
                if (obj instanceof JSONObject) {
                    resultArray.add(convertObject((JSONObject) obj));
                } else {
                    // 非对象类型直接添加
                    resultArray.add(obj);
                }
            }
            return resultArray.toStringPretty();
        } else {
            // 处理JSON对象
            JSONObject jsonObject = JSONUtil.parseObj(jsonStr);
            JSONObject resultObj = convertObject(jsonObject);
            return resultObj.toStringPretty();
        }
    }

    /**
     * 转换单个JSON对象（处理一级和二级结构）
     */
    public static JSONObject convertObject(JSONObject jsonObject) {
        JSONConfig jsonConfig = new JSONConfig();
        jsonConfig.setIgnoreNullValue(false);
        JSONObject result = new JSONObject(jsonConfig);

        for (String key : jsonObject.keySet()) {
            // 转换一级键名
            String firstLevelKey = NamingCase.toUnderlineCase(key);
            Object value = jsonObject.get(key);

            // 处理二级结构
            if (value instanceof JSONObject) {
                // 如果值是JSON对象，转换其内部键名
                JSONObject secondLevelObj = (JSONObject) value;
                JSONObject convertedSecondLevel = new JSONObject(jsonConfig);

                for (String secondKey : secondLevelObj.keySet()) {
                    String convertedSecondKey = NamingCase.toUnderlineCase(secondKey);
                    convertedSecondLevel.put(convertedSecondKey, secondLevelObj.get(secondKey));
                }
                result.put(firstLevelKey, convertedSecondLevel);
            }
            // 处理数组类型
            else if (value instanceof JSONArray) {
                JSONArray array = (JSONArray) value;
                JSONArray convertedArray = new JSONArray();

                for (Object item : array) {
                    if (item instanceof JSONObject) {
                        // 如果数组元素是对象，递归处理（最多两层）
                        JSONObject itemObj = (JSONObject) item;
                        JSONObject convertedItem = new JSONObject(jsonConfig);

                        for (String itemKey : itemObj.keySet()) {
                            convertedItem.put(NamingCase.toUnderlineCase(itemKey), itemObj.get(itemKey));
                        }
                        convertedArray.add(convertedItem);
                    } else {
                        // 非对象类型直接添加
                        convertedArray.add(item);
                    }
                }
                result.put(firstLevelKey, convertedArray);
            }
            // 基本类型直接添加
            else {
                result.put(firstLevelKey, value);
            }
        }

        return result;
    }
}