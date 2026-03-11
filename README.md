# Runzo 测试执行平台

这是一个基于 `FastAPI + Jinja2 + HTMX` 的中文 Web 平台，用来把 `Runzo` 的训练模拟与结算脚本能力改造成可视化操作页面。

## 当前能力

- 在页面填写 `userId`、`Authorization`、断点起跑时间和用户画像参数
- 点击按钮后在服务端启动单任务后台执行流
- 按原脚本规则执行：
  - MongoDB 读取训练计划
  - 过滤 `Rest`
  - 按 `dayStartTime` 升序执行
  - 调用 `simulate`
  - 调用 `settlement`
  - 到达检查点时暂停，等待页面点击“继续执行”
- 提供任务状态页、日志面板和 JSON 状态接口

## 技术栈

- `FastAPI`
- `Jinja2`
- `HTMX`
- `httpx`
- `pymongo`
- `pytest`

## 安装与运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后访问 `http://127.0.0.1:8000`。

## 重要说明

- 第一版只支持单任务运行
- 不做数据库持久化
- 不写本地结果文件
- 服务重启后任务状态会丢失
- 敏感参数仅保存在服务端内存

## 环境变量

如果不配置，会使用当前项目内置的默认测试地址。

- `RUNZO_MONGO_DB`
- `RUNZO_MONGO_COLLECTION`
- `RUNZO_SIMULATE_URL`
- `RUNZO_TEST_MONGO_URI`
- `RUNZO_TEST_SETTLE_URL`
- `RUNZO_PREPROD_MONGO_URI`
- `RUNZO_PREPROD_SETTLE_URL`
- `RUNZO_DAY_SLEEP_SECONDS`
- `RUNZO_DEFAULT_LANG`
- `RUNZO_DEFAULT_TIME_ZONE`
- `RUNZO_DEFAULT_COUNTRY`

## 测试

```bash
pytest
```
# -Web-
