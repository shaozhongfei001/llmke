const chat_history_data_mock1 = {
  success: true,
  errorMsg: null,
  errorCode: null,
  data: {
    label: '变桨控制系统',
    sessionId: 'acd7261202bc13f69a54cef98c895a23',
    gmtCreate: '2024-08-13 14:41:03',
    gmtModified: '2024-08-21 18:23:15',
    createBy: 'admin',
    updateBy: 'admin',
    filePath: 'http://10.15.12.12:9000',
    queryReplyPairList: [
      {
        query: {
          id: 3678,
          gmtCreate: 1723531263000,
          content:
            '变桨控制系统调节风机桨叶迎风角使发电机保持恒功率输出。当强风导致风轮转速加快，会发生什噩梦？',
          type: 'text',
          queryId: 'chat-cd7261202bc13f69a54cef98c895a232',
          audioUrl: null,
        },
        reply: {
          id: 3663,
          gmtCreate: 1723531264000,
          content:
            '当强风导致风轮转速加快时，变桨控制系统会调节风机桨叶的迎风角，使转子减速。[1](链接的URL) 这种平稳的变桨动作有效地减少负载，从而保证发电机向电网提供的电能保持恒定功率输出，同时提高电能的兼容性。[1](链接的URL) 此外，变桨系统还能在强风情况下将叶片调整到安全位置（顺桨位置），以保护风机免受过度旋转的损害',
          type: 'text',
          reference:
            '[{"page_content":"变桨控制系统调节风机桨叶迎风角使发电机保持恒功率输出。当强风导致风轮转速 加快，桨叶平稳变桨，使转子减速，有效地减少负载，保证供向电网的电能具有较高的 兼容性。除了控制功率输出，变桨装置也是安全/制动系统。每一支叶片的变桨装置都 是相互独立的，在强风情况下每支叶片能旋转到一个安全位置（顺桨位置），使转子从 异常情况恢复到安全转速。每套变桨装置对风机的三支风机叶片分别进行控制，针对每支叶片的变桨距机构采 用一只旋转变压器和一只接近开关，旋转变压器安装在驱动电机后部，用于检测电机轴 的旋转角度值，接近开关安装在变桨轴承 70°附近，用于校验旋转变压器的角度值。每 套变桨装置都带有限位开关，当叶片转到极限位置时，叶片上的限位开关板触动限位开 关，使叶片停止转动。当电网异常、外部电源或控制单元发生故障时，为了保证叶片仍能正常收桨，每只 叶片配备独立的超级电容模组作为后备电源。3.1轴控柜本套变桨系统配有三个轴控柜，每个轴控柜控制一支叶片。轴控柜内的驱动器接收 变桨系统控制器的命令，对变桨电机的转速、转向进行控制。每个轴控柜中均配有六个 超级电容模组，分别作为三支桨叶安全顺桨的后备电源。当风机需要紧急顺桨且电网异 常时，超级电容进行供电，以保障叶片安全顺桨到风暴位置。变桨系统轴控柜内元器件 有差异，变桨系统三个轴控柜的布局略有不同。轴控柜 3中安装有变桨 PLC。变桨系统 轴控柜如图 3-1所示。","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus","es"]},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":1.2769300627708435},{"page_content":"注意：当环境温度较低时，需要先将 10F1合上后，加热到上电的温湿度要求，再合上 1F1给变桨系统上电。在风场组装叶片时，将叶片后缘摆成竖直向上，通过手动操作盒调桨，将变桨轴承 内圈的零刻度线转到和叶片的零刻度线对齐，然后装上叶片，按照工艺文件要求力 矩值固定拧紧叶根螺栓，一切准备工作就绪后，结合风场环境条件吊装叶片。图 5-3 手操盒 变桨系统有自动运行，紧急运行，手动运行三种运行模式。5-16运行模式6.1自动控制运行模式在自动控制模式下，风机主控制器与变桨控制器，变桨控制器和三个变桨驱动器之 间通过 CANopen建立数据交换。功能描述：风机主控系统和变桨系统之间采用 CAN总线通讯方式。三支叶片的转动控制回路：变桨控制器给定驱动器的目标位置、速度限值、加减速度限值等控制指令。 驱动器采用从内到外依次为电流（转矩）、速度、位置的三闭环控制方式。电流 环具有电流回路自整定功能，实现转矩控制；速度环采用 PID算法通过速度反 馈实现对三相电压与频率的控制；位置环采用比例加前馈算法实现位置的精确 定位控制。","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus","es"]},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.654782454835044},{"page_content":"<table>\\n<tr><td>操作</td><td>风速条件</td><td>备注</td></tr>\\n<tr><td>进入机舱作业</td><td>平均风速≤13m/s</td><td>平均风速大于此风速时，应从风机中撤出。</td></tr>\\n<tr><td>使用风轮锁 \\\\n（三只叶片都在顺\\\\n桨位置）</td><td>平均风速≤11m/s</td><td>风速超过此限值，而风轮又被锁住的话，会\\\\n对风机造成相当大的损害，因此，风速在此\\\\n限值以上时风轮锁必须无条件解锁。</td></tr>\\n<tr><td>进入轮毂作业 \\\\n（三只叶片都在顺\\\\n桨位置）</td><td>平均风速≤11 m/s</td><td>三只叶片都在顺桨位置，紧急停机按钮已启\\\\n动、风轮已被锁住而且平均风速≤11 m/s 才\\\\n允许在轮毂内工作。</td></tr>\\n<tr><td>进入轮毂作业 \\\\n（一只叶片没在顺\\\\n桨位置）</td><td>平均风速≤10 m/s</td><td>因变桨系统故障，一只叶片没在顺桨位置\\\\n（90°变桨角度），只有在紧急停机按钮已启\\\\n动、风轮已被锁住并且平均风速达到\\\\nv≤10m/s 才允许在轮毂内部工作，如果风速\\\\n高于此水平，则工作必须暂停，所有人员必\\\\n须离开轮毂。</td></tr>\\n<tr><td>调整单只叶片桨矩</td><td>平均风速≤10 m/s</td><td>只有当风速不超过10 m/（s 10分钟平均值）、\\\\n风轮被锁住的情况下，才能调整单只叶片桨\\\\n矩（其它两只叶片保持在 90°顺桨位置）。</td></tr>\\n<tr><td>注意：如果三只叶片均未在顺桨位置（90°变桨角度），同时风轮刹车也未运行，风轮\\\\n锁必须保持工作。如果平均风速＞8 m/s，必须立即从风机及其周围撤出。</td></tr>\\n</table>","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["es"]},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.6288894057273865},{"page_content":"6.3手动运行模式警告：叶片的手动运行如果操作错误，可能会导致人身安全问题。在人工操作变桨 系统之前，必须先采取所有必要的安全保护措施。为此，参考适当的操作指示，注 意设备制造商的安全措施。警告：手动操作前必须确保风轮锁锁住轮毂；只有在风速不高于 10m/s时才能进行手动操作；同一时间只允许有一只桨叶从停放位置移动出来，在移动第二只桨叶时，应先 保证第一只桨叶重新回到 92°顺桨位置。变桨手动运行操作方法：进行手动操作之前务必确保所有轴的超级电容维护开关 7Q1处于“OFF”状态、 桨叶处于风暴位置；将轴控柜 3柜外的“手动维护开关”打到“ON”；将手动操作和连接到相应的轴控柜，插头标识为“SM”；按要求依次对系统进行上电，上电顺序：1Q1、10F1、1F1、2F2、13F1、13F2、 14F1、14F2。将手动操作盒上的“驱动器使能”开关打到开使能；设定需要的手动变桨速度和方向；手动正反转按钮：开桨：方向是从 92°到 0°；收桨：方向是从 0°到 92°。手动快慢速按钮：慢速：1°/s；快速：3°/s。点击手动运行按钮，执行手动变桨操作。注意：仅允许在 0°到 92°位置范围手动移动叶片。","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus","es"]},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.6088034879077564},{"page_content":"位置控制 速度控制 电流控制电机 变桨齿 轮箱 + +接近开关+旋转 变压 器主控给 定位置 电流 传感器 功率变换器位置速度东方风电 东方风电东方风电 东方风电图 6-1 变桨闭环控制示意图6.2紧急运行模式当“紧急收桨指令”触发时，变桨系统会进行 92°紧急收桨。所有桨叶将以设定 的速度移动到 92°顺桨位置处。注意：当紧急收桨指令激活时，若电网电源和超级电容电源均可用，优先使用电网 电源驱动叶片。功能描述：为能启动紧急顺桨，必须激活伺服驱动器的“DI3：驱动器急停”数字量输入（24V 掉电），同时后备电源必须可用。数字量输入“驱动器急停”在以下几种情况下会被激活：相应风机主控安全链打开；驱动器故障；变桨 PLC故障；风机通讯滑环测速传感器检测到超速；电网异常超过 3s。6-1东方风电 东方风电东方风电 东方风电紧急收桨桨叶转速变化如下：当触发“紧急收桨”指令时，变桨系统控制桨叶先以 3°/s的速度运行到 88°，再以 0.5°/s的速度运行到 92°限位开关处。注意：在“紧急收桨”期间，定位运动是由驱动器控制的。","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus","es"]},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.5436798473199208}]',
          queryId: 'chat-cd7261202bc13f69a54cef98c895a232',
          feedbackResult: null,
          feedbackId: null,
          parsedFilePaths: [
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
          ],
        },
      },
      {
        query: {
          id: 3691,
          gmtCreate: 1724231467000,
          content: 'java学习路线',
          type: 'text',
          queryId: 'chat-ce3512062fd9158179372d70d5b0b220',
          audioUrl: null,
        },
        reply: {
          id: 3676,
          gmtCreate: 1724231469000,
          content:
            '对不起，您的问题与提供的资料内容不符。<a id="0">[1]</a>您提到的是“java学习路线”，而提供的资料主要涉及AP70A-HMI_V1_01调试软件和Lenze EasyStarter软件的安装步骤，以及UPS系统、电池组的工作原理、设备规范和维护等内容。如果您需要关于Java学习路线的建议，我可以提供以下基本的指导：\n\n1. **基础知识**：首先，学习Java的基础语法，包括变量、数据类型、运算符、控制结构（如if-else，for，while等）、数组和集合。\n\n2. **面向对象编程**：理解类、对象、封装、继承和多态等面向对象编程的基本概念。\n\n3. **Java SE**：深入学习Java标准版（Java Standard Edition，SE），包括IO流、多线程、网络编程、集合框架、异常处理、正则表达式等。\n\n4. **Java异常处理**：学习如何使用try-catch-finally语句处理程序中的异常。\n\n5. **集合框架**：熟悉ArrayList、LinkedList、HashMap等常用集合类的使用。\n\n6. **Java泛型**：了解泛型的概念和使用，以提高代码的类型安全性和可读性。\n\n7. **设计模式**：学习一些常见的设计模式，如工厂模式、单例模式、观察者模式等。\n\n8. **Java Swing/AWT**：学习创建桌面应用程序的界面设计。\n\n9. **JDBC**：学习如何使用Java进行数据库操作，包括连接数据库、执行SQL语句、处理结果集等。\n\n10. **框架学习**：学习至少一个Java Web开发框架，如Spring、Struts或Hibernate，理解MVC设计模式。\n\n11. **Spring框架**：深入学习Spring框架，包括IoC（控制反转）、DI（依赖注入）、AOP（面向切面编程）等。\n\n12. **Spring Boot**：学习Spring Boot，它简化了Sp',
          type: 'text',
          reference:
            '[{"page_content":"2) 进入 AP70A-HMI_V1_01调试软件安装向导，点击“下一步”；3) 选择安装文件夹，可通过“浏览”按钮安装在任意盘，默认为 C:\\\\AP70A_HMI_V1.01\\\\， 并选中“任何人”按钮，点击“下一步”； 8-14) 进入“确认安装”页面，直接点击“下一步”，进行安装；5) 点击“关闭”，完成 AP70A调试软件的安装。8.2 lenze软件安装（以 AP70A系统为例）8.2.1 lenze EasyStarter软件安装1) 打开文件夹中的 Easystarter文件，双击“Setup.exe”应用程序开始安装；选择语言 为“U.S.English”，点击“OK”；2) 直接点击“Next”进入下一步；3) 点击“Yes”；8-24) 在 Name处输入名字，Company输入公司名，License number可不填写，点击“Next”；5) 可通过“Browse”选择安装路径，点击“Next”；（请安装余量较大的磁盘进行安装， 防止安装空间不足）；8-36) 继续点击“Next”；7) 开始安装，可能需要 3-5分钟左右，请勿进行任何操作，待安装完成后自动进入安 装完成页面；8-48) 点击“finish”后出现下图所示的指示信息，表示软件没有连接到 Lenze驱动器，可 直接点击“确定”。8.2.2 安装 EasyStarter下载 8400新 Firmware时需要的设备描述文件1) 打开开始菜单lenzeEasy package manage；2) 在下图中点击“import”；3) 选择附件中的 Packages，然后点击“OK”；8-54) 然后在“Import packages”页面，点击“Install”；","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":""},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.1412273355387151},{"page_content":"3.8 旁路电源调压有自动和手动两种方式。3.9 UPS系统配备变送器和报警总信号。4 检修4.1 检修类别及周期4.2 检修标准项目4.3 总则4.3.1  检验前的准备要求在进行检验之前，工作(试验)人员应认真学习《继电保护和电网安全自动装置现场工作保安规定》、《继电保护及电网安全自动装置检验条例》和本规程，理解和熟悉检验内容和要求。4.3.2  试验设备及试验接线的基本要求（1）为了保证检验质量，应使用继电保护微机型试验装置，其技术性能应符合部颁DL/T 619—1510《继电保护微机型试验装置技术条件》的规定。（2）试验仪表应经检验合格，其精度应不低于0.5级。（3）试验回路的接线原则，应使加入保护装置的电气量与实际情况相符合。模拟故障的试验回路，应具备对保护装置进行整组试验的条件。4.3.3 外观及接线检查（1） UPS系统硬件配置、标注及接线等应符合图纸要求。（2） UPS系统各插件上的元器件的外观质量、焊接质量应良好，所有芯片应插紧，型号正确， 芯片放置位置正确。（3） UPS系统的背板接线有无断线、短路和焊接不良等现象，并检查背板上抗干扰元件的焊接、连线和元器件外观是否良好。","metadata":{"source":"dev-rag-data/sdtest1/十里界风电场检修规程.docx","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Y2B6YeM55WM6aOO55S15Zy65qOA5L+u6KeE56iLLmRvY3g=","search_type":["es"],"offset":null},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Y2B6YeM55WM6aOO55S15Zy65qOA5L+u6KeE56iLLmRvY3g=","score":0.14083760055713354},{"page_content":"装设一组220V 200AH固定型阀控密封式铅酸蓄电池。通讯蓄电池3.2 设备规范4 电池组工作原理4.1 蓄电池工作原理蓄电池是一种化学电源，它的充、放电过程是电能与化学能的相互转换过程，充电时将电能转化为化学能，反之将化学能转化为电能。放电时：PbO2＋Pb＋2H2SO4放电→2PbSO4＋2H2O放电时正、负极板都形成了硫酸铅，析出了水，使电解液比重减小，因PbSO4的电阻比有效物质大得多，所以放电时蓄电池内阻增大，端电压降低，正极板由原来的深棕色变成红褐色，负极由原来的淡灰色变成深灰色。充电时：2PbSO4＋2H2O充电→PbO2＋Pb＋2H2SO4充电时，蓄电池正极板还原为PbO2，负极板还原为铅，析出两个分子的硫酸，因此电解液比重增加，内阻减小，端电压升高，正负极板的颜色由暗淡变为新鲜。4.2 阀控铅酸蓄电池组的分类：阀控铅酸蓄电池主要有两类，一类为贫液式，即阴极吸收式极板细玻璃纤维膜电池。另一类为胶体电池。其原理和结构都是在原铅酸蓄电池基础上，采取措施使氧气循环复合及对氢气产生拟制，任何氧气的产生都认为是水的损失。如果水过量消耗，就会使电池干涸失效，电池内阻增大而导致蓄电池容量的损失。","metadata":{"source":"dev-rag-data/sdtest1/十里界风电场检修规程.docx","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Y2B6YeM55WM6aOO55S15Zy65qOA5L+u6KeE56iLLmRvY3g=","search_type":["es"],"offset":null},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Y2B6YeM55WM6aOO55S15Zy65qOA5L+u6KeE56iLLmRvY3g=","score":0.11862157980600992},{"page_content":"<table>\\n<tr><td>版本号 \\\\nRevision No.</td><td>日期  \\\\nRelease date</td><td>换 版 说 明  \\\\nRevision description</td></tr>\\n<tr><td>A</td><td>2018.3</td><td>首次发布</td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n</table>","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":""},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.11706946548462534},{"page_content":"<table>\\n<tr><td>维护工作内容方案</td><td>重复性</td><td>解释</td><td>维护清单</td></tr>\\n<tr><td>500小时维护</td><td>不重复</td><td>首次运行后500小时的维护内容</td><td>500小时维护清单</td></tr>\\n<tr><td>半年维护</td><td>重复</td><td>首次运行后半年期的维护内容</td><td>半年维护清单</td></tr>\\n<tr><td>每年维护</td><td>重复</td><td>首次运行后每年期的维护内容</td><td>每年维护清单</td></tr>\\n</table>","metadata":{"source":"dev-rag-data/sdtest1/十里界风电场检修规程.docx","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Y2B6YeM55WM6aOO55S15Zy65qOA5L+u6KeE56iLLmRvY3g=","search_type":["milvus"],"offset":""},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Y2B6YeM55WM6aOO55S15Zy65qOA5L+u6KeE56iLLmRvY3g=","score":0.10078361690975725}]',
          queryId: 'chat-ce3512062fd9158179372d70d5b0b220',
          feedbackResult: null,
          feedbackId: null,
          parsedFilePaths: [
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/十里界风电场检修规程.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/十里界风电场检修规程.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/十里界风电场检修规程.txt',
          ],
        },
      },
      {
        query: {
          id: 3692,
          gmtCreate: 1724235387000,
          content: '你是谁？',
          type: 'text',
          queryId: 'chat-064a84796d435a04fc3418c98ac0fe2d',
          audioUrl: null,
        },
        reply: {
          id: 3677,
          gmtCreate: 1724235389000,
          content:
            '我是AI助手，能为您提供信息查询、问题解答等帮助。如果您有关于风力发电机组变桨系统使用维护、交易法规或其他相关问题，都可以向我提问。但请注意，我提供的所有信息都基于我所训练的数据，对于保密信息或特定的敏感问题，我会遵循不泄露的原则。',
          type: 'text',
          reference:
            '[{"page_content":"密级：核心商密 Security Classification: Core SecretDONGFANG ELECTRICWIND POWER CO., LTD.风力发电机组变桨系统使用维护说明书 User Manual of the Pitch System of the Wind Turbine东方风电保密声明: 本文件及其所有附件为东方电气风电有限公司保密信息，收到 文件请妥善管理；未经许可，任何人不得进行传播、分发或复制。DONGFANG ELECTRICWIND POWER CONFIDENTIALITY: The informationcontained in this document (including any attachments) is the confidential information of Dongfang Electric Wind Power Co., Ltd., subject to copyright and for the use of theintended recipient only. Unauthorized retention, distribution or copying of this document is forbidden and may be actionable.换版记录 Revision list1-1目 录 Index章节 Chapter 标题名称 Chapter name 页码 Page概述运输与存储技术规范和测试标准 安装叶片吊装运行模式维护软件安装联机调试整定值车间及风场叶片校零 常见故障解决方案 13 16 1-21 概述1-1本使用维护说明书主要针对东方风电自主研发的 AP110型变桨系统的硬件系统和 软件系统的使用及维护进行说明。在进行变桨系统的安装、维护之前，必须遵守如下安 全规范：施工安全规范：维修人员必须年满 18岁且受过专业培训、具备维修和维护能力，只有受诶托的 工作人员才能在设备上工作；按照公司的管理制度，办理相关票证、登高作业证等；遵守国家规定的安全条例；遵守“三不伤害”原则，即不伤害自己，不伤害他人，不被他人伤害；","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":""},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.14546866795048116},{"page_content":"（2）接到排油阀上，另一端放入油桶里。检查放油管路，如无问题打开放油阀，将齿轮箱内的润滑油全部排出(注意过程中更换油桶)。排完后关闭排油阀。（3）检查齿轮箱内部清洁程度，用干洗剂清洗齿轮箱内部，清洗完毕后必需将清洗剂排干净，然后用少量的新润滑油冲洗。检查齿轮箱体、齿轮、轴承是否有损坏和潜伏危险。如果必需转动齿轮检查，你要判断风速是否足够小，转速没有加速度，打开叶轮锁和紧急刹车并让机舱偏航使得它不对着风，同时必需在紧急刹车按钮旁安排一位工作人员以备急需时按下紧急刹车。（4）通过油泵与过滤装置，将新润滑油过滤后泵入齿轮箱内。（5）加完油后将加油孔装配要求重新封好。并清理掉加油过程中所泄漏的润滑油。（6）再次检查加油孔、放油阀是否密封好。将空油桶吊到地面，加油完毕。4.9.14 齿轮箱油冷却与润滑系统的检查与维护（1）对冷却与润滑系统进行任何维护和检修，必须首先使风力发电机停止工作，各制动器处于制动状态并将叶轮锁锁定。","metadata":{"source":"dev-rag-data/sdtest1/十里界风电场检修规程.docx","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Y2B6YeM55WM6aOO55S15Zy65qOA5L+u6KeE56iLLmRvY3g=","search_type":["es"],"offset":null},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Y2B6YeM55WM6aOO55S15Zy65qOA5L+u6KeE56iLLmRvY3g=","score":0.14032936615752986},{"page_content":"情况需采取处理指施时请尽快与本厂联系。1.在第一运行的半年里，由每天换查一次逐渐减少到每周一次，运行半年后，减少到每半月和 月一次，运行一年以后，每一年进行检表 2.如果发现异常现象如严重甜油声音异常温 升太高振动胸烈等应停机热查，清除故障。3.油系采用的是骨面组合式DB）角接域轴承， 正常使用寿命为5年以上，当轴承严重磨 损时，必须及时更换配对的同种规格型号的指定精度的轴承， 判断轴承的异意，最简单的办法是检查运转声客 有无异常，可用直径5mm的钢排在轴承安装位置整听运转情况，运转声音应只有和谐的滑动声音。油的摩擦育及轴承保持架的轻微振动音，而无异 常声音时为正常，-12 组能有受的认面不发生市穿，电，洗 中为现定的定的 20标准现定， 尺可能为电爱波形、电的均方根为0.出！试验 合格后，重复绝终闻川认验，认电压为时 为lnin九、故障及排你万法推方法 6.随机文件1台格证 超升大A K34192品使用说明书3其它相关文件 二，订货须知 .订货时，请详细说明您新需的型 电大，调电工件","metadata":{"source":"dev-rag-data/sdtest1/主变压器设备说明书.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Li75Y+Y5Y6L5Zmo6K6+5aSH6K+05piO5LmmLnBkZg==","search_type":["es"],"offset":null},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Li75Y+Y5Y6L5Zmo6K6+5aSH6K+05piO5LmmLnBkZg==","score":0.11868982758993903},{"page_content":"<table>\\n<tr><td>版本号 \\\\nRevision No.</td><td>日期  \\\\nRelease date</td><td>换 版 说 明  \\\\nRevision description</td></tr>\\n<tr><td>A</td><td>2018.3</td><td>首次发布</td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n</table>","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":""},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.11859522046676525},{"page_content":"5.精专：试产品在额定锁我和正等使用条件下可 度S11作制运行，轴乐的好命为年以！ 家封什寿命：在正意使用条件下宗封元件应邮 10变器油，你时元日年命不少5年、续用后，如有 淮、密州配行需要更换，油泉使用专命10年七、安装与调试 收装前的准备工作1京在报运或配换时应平稳，轻放，打开包装箱检 夜说明书和型号是否符合要求，各零件应完好无损。轮转子起动应退速无摩擦现象 2东的安装系起动应灵活面无异常声音 3当电源处千平衡状态时，电动机任何一相的空 载电流与三相空线电流的平均值的偏差量应小于 10%（注油后再检查电流） 4联接配管时，接台部位不能温人杂物，装好密封3东的调试1油东与冷却器安装好后，将进口阀门开到 最大位置，使东内充满变压器油2排净系内空气，稳度完好后开始运行3）台上电源试运行，进行观案，油流维电器应工 作平稳4调整出油口流量，纯其法到额定点的运行状卷八.检与维护变压器油泵在运行时，电动机部分也充满了变用 器油以冷却电动机，同时，也使叶轮转子内旋转 的轴承得到润滑。若换我中发现有任何不良情况 时，必须停机拆卸换查，查明原因，对运转不良","metadata":{"source":"dev-rag-data/sdtest1/主变压器设备说明书.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Li75Y+Y5Y6L5Zmo6K6+5aSH6K+05piO5LmmLnBkZg==","search_type":["es"],"offset":null},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Li75Y+Y5Y6L5Zmo6K6+5aSH6K+05piO5LmmLnBkZg==","score":0.10364209851250052}]',
          queryId: 'chat-064a84796d435a04fc3418c98ac0fe2d',
          feedbackResult: null,
          feedbackId: null,
          parsedFilePaths: [
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/十里界风电场检修规程.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/主变压器设备说明书.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/主变压器设备说明书.txt',
          ],
        },
      },
      {
        query: {
          id: 3693,
          gmtCreate: 1724235793000,
          content: '你是谁',
          type: 'audio',
          queryId: 'chat-e5ce4291f8b7bf4cb2c3402e2bb476e8',
          audioUrl: 'dev-rag-data/audio/admin/2024-08-21/1724235789180/file.wav',
        },
        reply: {
          id: 3678,
          gmtCreate: 1724235795000,
          content:
            '我是专业的助手，能够帮助您解答关于风力发电机组变桨系统、维护、操作以及相关技术规范的问题。<a id="2">[3]</a>如果您有关于这些领域的疑问，欢迎提问。但请注意，我提供的信息基于我所训练的数据，对于保密信息或特定的敏感问题，我会遵循不泄露的原则。',
          type: 'audio',
          reference:
            '[{"page_content":"<table>\\n<tr><td>版本号 \\\\nRevision No.</td><td>日期  \\\\nRelease date</td><td>换 版 说 明  \\\\nRevision description</td></tr>\\n<tr><td>A</td><td>2018.3</td><td>首次发布</td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n<tr><td></td><td></td><td></td></tr>\\n</table>","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":""},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.14071709015173836},{"page_content":"（2）接到排油阀上，另一端放入油桶里。检查放油管路，如无问题打开放油阀，将齿轮箱内的润滑油全部排出(注意过程中更换油桶)。排完后关闭排油阀。（3）检查齿轮箱内部清洁程度，用干洗剂清洗齿轮箱内部，清洗完毕后必需将清洗剂排干净，然后用少量的新润滑油冲洗。检查齿轮箱体、齿轮、轴承是否有损坏和潜伏危险。如果必需转动齿轮检查，你要判断风速是否足够小，转速没有加速度，打开叶轮锁和紧急刹车并让机舱偏航使得它不对着风，同时必需在紧急刹车按钮旁安排一位工作人员以备急需时按下紧急刹车。（4）通过油泵与过滤装置，将新润滑油过滤后泵入齿轮箱内。（5）加完油后将加油孔装配要求重新封好。并清理掉加油过程中所泄漏的润滑油。（6）再次检查加油孔、放油阀是否密封好。将空油桶吊到地面，加油完毕。4.9.14 齿轮箱油冷却与润滑系统的检查与维护（1）对冷却与润滑系统进行任何维护和检修，必须首先使风力发电机停止工作，各制动器处于制动状态并将叶轮锁锁定。","metadata":{"source":"dev-rag-data/sdtest1/十里界风电场检修规程.docx","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Y2B6YeM55WM6aOO55S15Zy65qOA5L+u6KeE56iLLmRvY3g=","search_type":["es"],"offset":null},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Y2B6YeM55WM6aOO55S15Zy65qOA5L+u6KeE56iLLmRvY3g=","score":0.1400721511314623},{"page_content":"密级：核心商密 Security Classification: Core SecretDONGFANG ELECTRICWIND POWER CO., LTD.风力发电机组变桨系统使用维护说明书 User Manual of the Pitch System of the Wind Turbine东方风电保密声明: 本文件及其所有附件为东方电气风电有限公司保密信息，收到 文件请妥善管理；未经许可，任何人不得进行传播、分发或复制。DONGFANG ELECTRICWIND POWER CONFIDENTIALITY: The informationcontained in this document (including any attachments) is the confidential information of Dongfang Electric Wind Power Co., Ltd., subject to copyright and for the use of theintended recipient only. Unauthorized retention, distribution or copying of this document is forbidden and may be actionable.换版记录 Revision list1-1目 录 Index章节 Chapter 标题名称 Chapter name 页码 Page概述运输与存储技术规范和测试标准 安装叶片吊装运行模式维护软件安装联机调试整定值车间及风场叶片校零 常见故障解决方案 13 16 1-21 概述1-1本使用维护说明书主要针对东方风电自主研发的 AP110型变桨系统的硬件系统和 软件系统的使用及维护进行说明。在进行变桨系统的安装、维护之前，必须遵守如下安 全规范：施工安全规范：维修人员必须年满 18岁且受过专业培训、具备维修和维护能力，只有受诶托的 工作人员才能在设备上工作；按照公司的管理制度，办理相关票证、登高作业证等；遵守国家规定的安全条例；遵守“三不伤害”原则，即不伤害自己，不伤害他人，不被他人伤害；","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":""},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.11820697490281114},{"page_content":"情况需采取处理指施时请尽快与本厂联系。1.在第一运行的半年里，由每天换查一次逐渐减少到每周一次，运行半年后，减少到每半月和 月一次，运行一年以后，每一年进行检表 2.如果发现异常现象如严重甜油声音异常温 升太高振动胸烈等应停机热查，清除故障。3.油系采用的是骨面组合式DB）角接域轴承， 正常使用寿命为5年以上，当轴承严重磨 损时，必须及时更换配对的同种规格型号的指定精度的轴承， 判断轴承的异意，最简单的办法是检查运转声客 有无异常，可用直径5mm的钢排在轴承安装位置整听运转情况，运转声音应只有和谐的滑动声音。油的摩擦育及轴承保持架的轻微振动音，而无异 常声音时为正常，-12 组能有受的认面不发生市穿，电，洗 中为现定的定的 20标准现定， 尺可能为电爱波形、电的均方根为0.出！试验 合格后，重复绝终闻川认验，认电压为时 为lnin九、故障及排你万法推方法 6.随机文件1台格证 超升大A K34192品使用说明书3其它相关文件 二，订货须知 .订货时，请详细说明您新需的型 电大，调电工件","metadata":{"source":"dev-rag-data/sdtest1/主变压器设备说明书.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Li75Y+Y5Y6L5Zmo6K6+5aSH6K+05piO5LmmLnBkZg==","search_type":["es"],"offset":null},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEv5Li75Y+Y5Y6L5Zmo6K6+5aSH6K+05piO5LmmLnBkZg==","score":0.11783199626176306},{"page_content":"<table>\\n<tr><td>编  号  Document No.</td><td>AP110A-VA00ASM</td></tr>\\n<tr><td>版本号  Revision No.</td><td>A</td></tr>\\n<tr><td>编  制  Editor</td><td>王 淋20190513</td></tr>\\n<tr><td>校  对  Checker</td><td>阳静20190513</td></tr>\\n<tr><td>审  核  Verifier</td><td>李 博20190513</td></tr>\\n<tr><td>会  签  Countersign</td><td>罗 婧20190513</td></tr>\\n<tr><td>罗 婧20190513</td></tr>\\n<tr><td>批  准  Approver</td><td>余 业祥20190516</td></tr>\\n</table>","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":""},"type":"Document","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.1016347124474123}]',
          queryId: 'chat-e5ce4291f8b7bf4cb2c3402e2bb476e8',
          feedbackResult: null,
          feedbackId: null,
          parsedFilePaths: [
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/十里界风电场检修规程.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/主变压器设备说明书.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
          ],
        },
      },
    ],
    searchConfigDTO: {
      id: 111,
      status: 1,
      isDefault: 1,
      configJson:
        '{"config_name":"sdtest_config","description":null,"model_name":"Qwen1.5-32B-Chat","temperature":0.3,"max_tokens":4096,"knowledge_base_name":"sdtest1","top_k":10,"score_threshold":0.8,"prompt":"你是一个智能助手，请总结知识库的内容来回答问题,请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括“知识库中未找到您要的答案!","default":true,"similar_threshold":0.5}',
      name: 'sdtest_config',
      des: null,
      createBy: 'admin',
      gmtCreate: '2024-08-13 14:33:56',
      permission: null,
      model: false,
    },
  },
};

const chat_history_data_mock2 = {
  success: true,
  errorMsg: null,
  errorCode: null,
  data: {
    label: '迈普通信的注',
    sessionId: '1d650e4528788e0d1334f48d28cc4bb0',
    gmtCreate: '2024-08-23 10:06:54',
    gmtModified: '2024-08-23 10:27:25',
    createBy: 'admin',
    updateBy: 'admin',
    filePath: 'http://10.15.12.12:9000',
    queryReplyPairList: [
      {
        query: {
          id: 3767,
          gmtCreate: 1724378814000,
          content: '迈普通信的注册资本是多少？',
          type: 'text',
          queryId: 'chat-d650e4528788e0d1334f48d28cc4bb08',
          audioUrl: null,
        },
        reply: {
          id: 3757,
          gmtCreate: 1724378815000,
          content: '2.3亿元',
          type: 'text',
          reference:
            '[{"page_content":"迈普通信的注册资本是多少？","metadata":{"source":"中国电子在川企业基本情况20240526.docx","id":"1759","search_type":["milvus"],"offset":"","order_num":"3"},"type":"Document","faq_answer":"2.3亿元","id":"1759","score":1.0466348377863566}]',
          queryId: 'chat-d650e4528788e0d1334f48d28cc4bb08',
          feedbackResult: null,
          feedbackId: null,
          parsedFilePaths: [''],
        },
      },
      {
        query: {
          id: 3768,
          gmtCreate: 1724379418000,
          content: '迈普通信的注册资本是多少？',
          type: 'text',
          queryId: 'chat-196b64d2483609a93d3d8e1235ec5a08',
          audioUrl: null,
        },
        reply: {
          id: 3759,
          gmtCreate: 1724379419000,
          content: '2.3亿元',
          type: 'text',
          reference:
            '[{"page_content":"迈普通信的注册资本是多少？","metadata":{"source":"中国电子在川企业基本情况20240526.docx","id":"1759","search_type":["milvus"],"offset":"","order_num":"3"},"type":"Document","faq_answer":"2.3亿元","id":"1759","score":1.0466348377863566}]',
          queryId: 'chat-196b64d2483609a93d3d8e1235ec5a08',
          feedbackResult: null,
          feedbackId: null,
          parsedFilePaths: [''],
        },
      },
      {
        query: {
          id: 3769,
          gmtCreate: 1724379492000,
          content: '迈普通信的注册资本是多少?',
          type: 'text',
          queryId: 'chat-b64d2483609a93d3d8e1235ec5a08a59',
          audioUrl: null,
        },
        reply: {
          id: 3760,
          gmtCreate: 1724379493000,
          content: '2.3亿元',
          type: 'text',
          reference:
            '[{"page_content":"迈普通信的注册资本是多少？","metadata":{"source":"中国电子在川企业基本情况20240526.docx","id":"1759","search_type":["milvus"],"offset":"","order_num":"3"},"type":"Document","faq_answer":"2.3亿元","id":"1759","score":1.0466348377863566}]',
          queryId: 'chat-b64d2483609a93d3d8e1235ec5a08a59',
          feedbackResult: null,
          feedbackId: null,
          parsedFilePaths: [''],
        },
      },
      {
        query: {
          id: 3770,
          gmtCreate: 1724379505000,
          content: '变桨系统的作业时风速要求时什么？',
          type: 'text',
          queryId: 'chat-4d2483609a93d3d8e1235ec5a08a59ee',
          audioUrl: null,
        },
        reply: {
          id: 3761,
          gmtCreate: 1724379506000,
          content: '',
          type: 'text',
          reference:
            '[{"page_content":"6.3手动运行模式警告：叶片的手动运行如果操作错误，可能会导致人身安全问题。在人工操作变桨 系统之前，必须先采取所有必要的安全保护措施。为此，参考适当的操作指示，注 意设备制造商的安全措施。警告：手动操作前必须确保风轮锁锁住轮毂；只有在风速不高于 10m/s时才能进行手动操作；同一时间只允许有一只桨叶从停放位置移动出来，在移动第二只桨叶时，应先 保证第一只桨叶重新回到 92°顺桨位置。变桨手动运行操作方法：进行手动操作之前务必确保所有轴的超级电容维护开关 7Q1处于“OFF”状态、 桨叶处于风暴位置；将轴控柜 3柜外的“手动维护开关”打到“ON”；将手动操作和连接到相应的轴控柜，插头标识为“SM”；按要求依次对系统进行上电，上电顺序：1Q1、10F1、1F1、2F2、13F1、13F2、 14F1、14F2。将手动操作盒上的“驱动器使能”开关打到开使能；设定需要的手动变桨速度和方向；手动正反转按钮：开桨：方向是从 92°到 0°；收桨：方向是从 0°到 92°。手动快慢速按钮：慢速：1°/s；快速：3°/s。点击手动运行按钮，执行手动变桨操作。注意：仅允许在 0°到 92°位置范围手动移动叶片。","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":"","order_num":null},"type":"Document","faq_answer":null,"id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":1.0419151544570924},{"page_content":"<table>\\n<tr><td>操作</td><td>风速条件</td><td>备注</td></tr>\\n<tr><td>进入机舱作业</td><td>平均风速≤13m/s</td><td>平均风速大于此风速时，应从风机中撤出。</td></tr>\\n<tr><td>使用风轮锁 \\\\n（三只叶片都在顺\\\\n桨位置）</td><td>平均风速≤11m/s</td><td>风速超过此限值，而风轮又被锁住的话，会\\\\n对风机造成相当大的损害，因此，风速在此\\\\n限值以上时风轮锁必须无条件解锁。</td></tr>\\n<tr><td>进入轮毂作业 \\\\n（三只叶片都在顺\\\\n桨位置）</td><td>平均风速≤11 m/s</td><td>三只叶片都在顺桨位置，紧急停机按钮已启\\\\n动、风轮已被锁住而且平均风速≤11 m/s 才\\\\n允许在轮毂内工作。</td></tr>\\n<tr><td>进入轮毂作业 \\\\n（一只叶片没在顺\\\\n桨位置）</td><td>平均风速≤10 m/s</td><td>因变桨系统故障，一只叶片没在顺桨位置\\\\n（90°变桨角度），只有在紧急停机按钮已启\\\\n动、风轮已被锁住并且平均风速达到\\\\nv≤10m/s 才允许在轮毂内部工作，如果风速\\\\n高于此水平，则工作必须暂停，所有人员必\\\\n须离开轮毂。</td></tr>\\n<tr><td>调整单只叶片桨矩</td><td>平均风速≤10 m/s</td><td>只有当风速不超过10 m/（s 10分钟平均值）、\\\\n风轮被锁住的情况下，才能调整单只叶片桨\\\\n矩（其它两只叶片保持在 90°顺桨位置）。</td></tr>\\n<tr><td>注意：如果三只叶片均未在顺桨位置（90°变桨角度），同时风轮刹车也未运行，风轮\\\\n锁必须保持工作。如果平均风速＞8 m/s，必须立即从风机及其周围撤出。</td></tr>\\n</table>","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":"","order_num":null},"type":"Document","faq_answer":null,"id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":1.04074281056722},{"page_content":"要做好安全防护工作：高空作业要系好安全带，戴安全帽，正确穿戴工作服， 劳保鞋，手套等；避免交叉作业，交叉作业应采取隔离防护；带电操作时，应按照安全规程送电，并做好绝缘保护工作，避免直接接触带电 体。安全注意事项：风机中作业的风速要求 注：平均风速为 10分钟平均值进入轮毂作业请务必锁上风轮锁！为避免意外伤害，进入轮毂内作业先断开变桨后备电源维护开关！轮毂区域内空间狭小，请特别注意人身及设备安全！手动操作桨叶时必须保证另外两个未操作桨叶回桨在限位开关处，不能多个桨 叶同时展开操作！本维护说明书中带“！”符号的文字与安全相关，应引起注意。收尾工作在安装维护工作完成后必须遵循以下步骤使风力发电机组重新投入运行：确认轮毂柜体内无其他杂物后，关闭轮毂内柜体柜门并锁紧；清除工作中产生的废弃物，将使用工具全部从轮毂拿出；离开轮毂后，松开叶轮锁；将所有机舱内紧急停机开关松开；清除带有维修作业提示的牌子。 吊装工作应根据被吊装机械的重量进行选择。变桨系统应存放在干燥、无振动的环 境中。","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":"","order_num":null},"type":"Document","faq_answer":null,"id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":1.0333726140168997},{"page_content":"6-27-17维护7.1 概述警告：◼进入轮毂前，确保风轮锁锁紧，限位开关被触发；◼轮毂内维护人员不得少于 2人；◼维护人员在轮毂内维护时，风速必须低于 11 m/s；◼停机维护时，有一支叶片指向地面并处于 90°顺桨位置；◼离开轮毂时，确保柜门锁锁紧。7.2定期维护变桨系统在强振动环境下运行，因此在运行一段时间后系统内固定螺钉或螺栓连接 可能会松弛，所以有必要定期检查并紧固可以接触到的螺栓和螺钉。同时服务人员应定 期对变桨电机、伺服驱动器、充电器、超级电容、加热器及柜体建连接电缆等部件进行 检查。具体检修计划如下表所示，并应做好相应记录,各部件维护项目请严格按照相关 操作规范执行：7-2东方风电7-38软件安装8.1变桨调试软件安装（以 AP70A系统为例）1) 双击文件，若是调试电脑已经安装Microsoft .NETFramework 4.0，直接进入步骤 2）；若是调试电脑未安装Microsoft .NET Framework 4.0，安装变桨调试软件程序的过程中会自动进入Microsoft .NET Framework 4.0安 装页面，如下图所示：点击“接受”，安装Microsoft .NET Framework 4.0：","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":"","order_num":null},"type":"Document","faq_answer":null,"id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.9212687026370655}]',
          queryId: 'chat-4d2483609a93d3d8e1235ec5a08a59ee',
          feedbackResult: null,
          feedbackId: null,
          parsedFilePaths: [
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
          ],
        },
      },
      {
        query: {
          id: 3772,
          gmtCreate: 1724379711000,
          content: '变桨系统的作业时风速要求时什么？',
          type: 'text',
          queryId: 'chat-596eafda3d3badb122fbaca12a37ab7c',
          audioUrl: null,
        },
        reply: {
          id: 3763,
          gmtCreate: 1724379713000,
          content: '',
          type: 'text',
          reference:
            '[{"page_content":"6.3手动运行模式警告：叶片的手动运行如果操作错误，可能会导致人身安全问题。在人工操作变桨 系统之前，必须先采取所有必要的安全保护措施。为此，参考适当的操作指示，注 意设备制造商的安全措施。警告：手动操作前必须确保风轮锁锁住轮毂；只有在风速不高于 10m/s时才能进行手动操作；同一时间只允许有一只桨叶从停放位置移动出来，在移动第二只桨叶时，应先 保证第一只桨叶重新回到 92°顺桨位置。变桨手动运行操作方法：进行手动操作之前务必确保所有轴的超级电容维护开关 7Q1处于“OFF”状态、 桨叶处于风暴位置；将轴控柜 3柜外的“手动维护开关”打到“ON”；将手动操作和连接到相应的轴控柜，插头标识为“SM”；按要求依次对系统进行上电，上电顺序：1Q1、10F1、1F1、2F2、13F1、13F2、 14F1、14F2。将手动操作盒上的“驱动器使能”开关打到开使能；设定需要的手动变桨速度和方向；手动正反转按钮：开桨：方向是从 92°到 0°；收桨：方向是从 0°到 92°。手动快慢速按钮：慢速：1°/s；快速：3°/s。点击手动运行按钮，执行手动变桨操作。注意：仅允许在 0°到 92°位置范围手动移动叶片。","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":"","order_num":null},"type":"Document","faq_answer":null,"id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":1.0419151544570924},{"page_content":"<table>\\n<tr><td>操作</td><td>风速条件</td><td>备注</td></tr>\\n<tr><td>进入机舱作业</td><td>平均风速≤13m/s</td><td>平均风速大于此风速时，应从风机中撤出。</td></tr>\\n<tr><td>使用风轮锁 \\\\n（三只叶片都在顺\\\\n桨位置）</td><td>平均风速≤11m/s</td><td>风速超过此限值，而风轮又被锁住的话，会\\\\n对风机造成相当大的损害，因此，风速在此\\\\n限值以上时风轮锁必须无条件解锁。</td></tr>\\n<tr><td>进入轮毂作业 \\\\n（三只叶片都在顺\\\\n桨位置）</td><td>平均风速≤11 m/s</td><td>三只叶片都在顺桨位置，紧急停机按钮已启\\\\n动、风轮已被锁住而且平均风速≤11 m/s 才\\\\n允许在轮毂内工作。</td></tr>\\n<tr><td>进入轮毂作业 \\\\n（一只叶片没在顺\\\\n桨位置）</td><td>平均风速≤10 m/s</td><td>因变桨系统故障，一只叶片没在顺桨位置\\\\n（90°变桨角度），只有在紧急停机按钮已启\\\\n动、风轮已被锁住并且平均风速达到\\\\nv≤10m/s 才允许在轮毂内部工作，如果风速\\\\n高于此水平，则工作必须暂停，所有人员必\\\\n须离开轮毂。</td></tr>\\n<tr><td>调整单只叶片桨矩</td><td>平均风速≤10 m/s</td><td>只有当风速不超过10 m/（s 10分钟平均值）、\\\\n风轮被锁住的情况下，才能调整单只叶片桨\\\\n矩（其它两只叶片保持在 90°顺桨位置）。</td></tr>\\n<tr><td>注意：如果三只叶片均未在顺桨位置（90°变桨角度），同时风轮刹车也未运行，风轮\\\\n锁必须保持工作。如果平均风速＞8 m/s，必须立即从风机及其周围撤出。</td></tr>\\n</table>","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":"","order_num":null},"type":"Document","faq_answer":null,"id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":1.04074281056722},{"page_content":"要做好安全防护工作：高空作业要系好安全带，戴安全帽，正确穿戴工作服， 劳保鞋，手套等；避免交叉作业，交叉作业应采取隔离防护；带电操作时，应按照安全规程送电，并做好绝缘保护工作，避免直接接触带电 体。安全注意事项：风机中作业的风速要求 注：平均风速为 10分钟平均值进入轮毂作业请务必锁上风轮锁！为避免意外伤害，进入轮毂内作业先断开变桨后备电源维护开关！轮毂区域内空间狭小，请特别注意人身及设备安全！手动操作桨叶时必须保证另外两个未操作桨叶回桨在限位开关处，不能多个桨 叶同时展开操作！本维护说明书中带“！”符号的文字与安全相关，应引起注意。收尾工作在安装维护工作完成后必须遵循以下步骤使风力发电机组重新投入运行：确认轮毂柜体内无其他杂物后，关闭轮毂内柜体柜门并锁紧；清除工作中产生的废弃物，将使用工具全部从轮毂拿出；离开轮毂后，松开叶轮锁；将所有机舱内紧急停机开关松开；清除带有维修作业提示的牌子。 吊装工作应根据被吊装机械的重量进行选择。变桨系统应存放在干燥、无振动的环 境中。","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":"","order_num":null},"type":"Document","faq_answer":null,"id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":1.0333726140168997},{"page_content":"6-27-17维护7.1 概述警告：◼进入轮毂前，确保风轮锁锁紧，限位开关被触发；◼轮毂内维护人员不得少于 2人；◼维护人员在轮毂内维护时，风速必须低于 11 m/s；◼停机维护时，有一支叶片指向地面并处于 90°顺桨位置；◼离开轮毂时，确保柜门锁锁紧。7.2定期维护变桨系统在强振动环境下运行，因此在运行一段时间后系统内固定螺钉或螺栓连接 可能会松弛，所以有必要定期检查并紧固可以接触到的螺栓和螺钉。同时服务人员应定 期对变桨电机、伺服驱动器、充电器、超级电容、加热器及柜体建连接电缆等部件进行 检查。具体检修计划如下表所示，并应做好相应记录,各部件维护项目请严格按照相关 操作规范执行：7-2东方风电7-38软件安装8.1变桨调试软件安装（以 AP70A系统为例）1) 双击文件，若是调试电脑已经安装Microsoft .NETFramework 4.0，直接进入步骤 2）；若是调试电脑未安装Microsoft .NET Framework 4.0，安装变桨调试软件程序的过程中会自动进入Microsoft .NET Framework 4.0安 装页面，如下图所示：点击“接受”，安装Microsoft .NET Framework 4.0：","metadata":{"source":"dev-rag-data/sdtest1/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.pdf","id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","search_type":["milvus"],"offset":"","order_num":null},"type":"Document","faq_answer":null,"id":"ZGV2LXJhZy1kYXRhL3NkdGVzdDEvQVAxMTBBLVZBMDBBU01fQVAxMTBB5Y+Y5qGo57O757uf5L2/55So57u05oqk6K+05piO5LmmX0EucGRm","score":0.9212687026370655}]',
          queryId: 'chat-596eafda3d3badb122fbaca12a37ab7c',
          feedbackResult: null,
          feedbackId: null,
          parsedFilePaths: [
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
            'http://10.15.12.12:9000/dev-rag-data/sdtest1/parsed/AP110A-VA00ASM_AP110A变桨系统使用维护说明书_A.txt',
          ],
        },
      },
      {
        query: {
          id: 3775,
          gmtCreate: 1724380043000,
          content: '\n迈普通信的注册资本是多少?',
          type: 'text',
          queryId: 'chat-64c8fc8f49fcc612dcf0d50c61990582',
          audioUrl: null,
        },
        reply: {
          id: 3766,
          gmtCreate: 1724380045000,
          content: '2.3亿元',
          type: 'text',
          reference:
            '[{"page_content":"迈普通信的注册资本是多少？","metadata":{"source":"中国电子在川企业基本情况20240526.docx","id":"1759","search_type":["milvus"],"offset":"","order_num":"3"},"type":"Document","faq_answer":"2.3亿元","id":"1759","score":1.0466348377863566}]',
          queryId: 'chat-64c8fc8f49fcc612dcf0d50c61990582',
          feedbackResult: null,
          feedbackId: null,
          parsedFilePaths: [''],
        },
      },
    ],
    searchConfigDTO: {
      id: 111,
      status: 1,
      isDefault: 1,
      configJson:
        '{"config_name":"sdtest_config","description":null,"model_name":"Qwen1.5-32B-Chat","temperature":0.3,"max_tokens":4096,"knowledge_base_name":"sdtest1","top_k":10,"score_threshold":0.8,"prompt":"你是一个智能助手，请总结知识库的内容来回答问题,请列举知识库中的数据详细回答。当所有知识库内容都与问题无关时，你的回答必须包括“知识库中未找到您要的答案!","default":true}',
      name: 'sdtest_config',
      des: null,
      createBy: 'admin',
      gmtCreate: '2024-08-13 14:33:56',
      permission: null,
      model: false,
    },
  },
};

export { chat_history_data_mock1, chat_history_data_mock2 };
