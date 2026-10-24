package com.gientech.tools.database.infrastructure.calback;

import com.gientech.tools.database.domain.entity.TLTable;

public interface ParseFileCallback {
    void onComplete(TLTable rstTlTable);
}