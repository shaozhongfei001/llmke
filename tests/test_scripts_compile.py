"""所有脚本必须能编译：这条挡的是"引号打架"这类低级语法错误。

真实教训：我两次在中文说明里用了 ASCII 双引号嵌在双引号字符串内
（`"只验"限流"，未验…"`），`pytest` 收集时不报、直到某个检查函数被调用才炸，
而 Q 是长流程，等到那一步已经跑了几分钟。
"""

import compileall
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_all_scripts_compile():
    ok = compileall.compile_dir(os.path.join(REPO, "scripts"), quiet=1, force=True,
                                legacy=False)
    assert ok, "scripts/ 下有文件无法编译（语法错误）"
