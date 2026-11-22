# Sprint 5：标准字段映射与数据库连接器验证

## 标准映射交互

元数据目录字段详情增加标准映射入口：
1. 选择一个数据标准。
2. 系统读取该标准当前编辑版本。
3. 将当前物理字段映射到该标准版本。
4. 映射状态默认为“待核验”。
5. 字段详情展示已关联的标准编码、版本和映射状态。

后端元数据字段详情 API 返回标准映射信息，便于后续展示落标率和映射差异。

## 数据库连接器自动化验证

新增连接器配置测试，覆盖：
- SQL Server：mssql+pymssql
- Oracle：oracle+oracledb
- MySQL：mysql+pymysql
- PostgreSQL：postgresql+psycopg

自动化测试验证驱动方言、主机、端口、数据库/服务名、用户名、密码环境变量注入和连接参数。测试通过 mock engine 工厂完成，不需要 CI 暴露真实数据库密码或网络。

## 真实环境验收仍需执行

CI 只能验证连接配置构造，不等于目标内网实例连接成功。上线前仍需分别使用只读账号验证：
- TCP 网络连通性、防火墙策略和 TLS 配置
- SQL Server 数据库名/实例及登录权限
- Oracle service name 或 SID 配置
- MySQL 仅采集配置指定 database
- PostgreSQL schema 授权及系统目录读取权限
- 元数据重复采集后字段 ID 稳定，标准映射不丢失

真实账号密码只保存在受控服务器环境变量或 Docker secrets，不得提交 Git。
