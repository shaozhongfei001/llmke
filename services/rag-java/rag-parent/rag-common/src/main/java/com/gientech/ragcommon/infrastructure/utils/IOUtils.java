package com.gientech.ragcommon.infrastructure.utils;

import java.io.*;

public class IOUtils {
    public static void closeIO(InputStream inputStream, OutputStream outputStream) {
        if (inputStream != null) {
            try {
                inputStream.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
        if (outputStream != null) {
            try {
                outputStream.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    public static void closeIO(OutputStream outputStream) {
        if (outputStream != null) {
            try {
                outputStream.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    public static void closeIO(InputStream... inputStreams) {
        if (inputStreams != null && inputStreams.length > 0) {
            for (int i = 0; i < inputStreams.length; i++) {
                closeIO(inputStreams[i], null);
            }
        }
    }

    public static void closeIO(Reader... bfr) {
        if (bfr != null && bfr.length > 0) {
            for (int i = 0; i < bfr.length; i++) {
                closeIO(bfr[i]);
            }
        }
    }

    public static void closeIO(Reader reader) {
        if (reader != null) {
            try {
                reader.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    public static void closeIO(InputStreamReader isReader) {
        if (isReader != null) {
            try {
                isReader.close();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }
}


